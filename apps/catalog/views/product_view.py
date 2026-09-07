from django.db.models import Avg, Count, Exists, OuterRef, Prefetch, Q, Subquery
from django_filters import rest_framework as django_filters
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..models import Product, Review, ReviewStatus
from ..models.product_model import ProductImage, ProductVariant
from ..serializers import (
    ProductDetailSerializer,
    ProductListSerializer,
    ReviewReadSerializer,
)


class AliasingOrderingFilter(filters.OrderingFilter):
    """
    Extends DRF's `OrderingFilter` with two things the plain version can't do:

    1. Public param aliases. Plain `OrderingFilter` only ever accepts
       `?ordering=<queryset_field>`. The (field, label) tuple form of
       `ordering_fields` does NOT rename the query parameter — the first
       element is always the real field name that must appear in the URL;
       the second is just a display label for the browsable API. So
       `ordering_fields = [('min_price', 'price')]` still requires
       `?ordering=min_price`, never `?ordering=price`. Here, each requested
       term is looked up in `view.ordering_param_aliases` (public name ->
       real field/annotation name) and rewritten *before* DRF's normal
       validation runs, so callers can use a friendly name (`price`) for an
       internal annotation (`min_price`).

    2. Deterministic, "grouped" ordering that's stable across pages.
       - `view.ordering_priority_fields`: fields prepended to *every*
         ordering, regardless of what the client requested or the default.
         We use this to always push products with no active variant to the
         very end of the list, no matter which field/direction is used to
         sort the rest.
       - A trailing `-id` tie-breaker is appended automatically if the
         resolved ordering doesn't already end on `id`. Without a fully
         deterministic ORDER BY, rows that tie on the requested field(s)
         can come back in a different relative order on different pages
         (or even on repeated requests for the same page), which would let
         a "no variant" product leak onto an earlier page or a "has
         variant" product get skipped/duplicated across pages.
    """

    def get_ordering(self, request, queryset, view):
        ordering_param = request.query_params.get(self.ordering_param)
        aliases = getattr(view, 'ordering_param_aliases', {})

        if ordering_param:
            requested = [term.strip() for term in ordering_param.split(',') if term.strip()]
            aliased = [self._apply_alias(term, aliases) for term in requested]
            ordering = self.remove_invalid_fields(queryset, aliased, view, request)
        else:
            ordering = None

        if not ordering:
            ordering = self.get_default_ordering(view) or ()

        return self._finalize(view, list(ordering))

    @staticmethod
    def _apply_alias(term, aliases):
        sign = '-' if term.startswith('-') else ''
        name = term.lstrip('-')
        return sign + aliases.get(name, name)

    @staticmethod
    def _finalize(view, ordering):
        priority = list(getattr(view, 'ordering_priority_fields', ()))
        # Don't let a priority field also appear later in the user-chosen
        # ordering (would be redundant / could conflict on direction).
        priority_names = {field.lstrip('-') for field in priority}
        ordering = [field for field in ordering if field.lstrip('-') not in priority_names]

        combined = priority + ordering
        if not any(field.lstrip('-') == 'id' for field in combined):
            combined.append('-id')
        return combined


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class CharInFilter(django_filters.BaseInFilter, django_filters.CharFilter):
    pass


class ProductFilter(django_filters.FilterSet):
    collections = CharInFilter(field_name='collections__slug', lookup_expr='in', label='Collection slugs')
    category = django_filters.CharFilter(field_name='category__slug', label='Category slug')
    featured = django_filters.BooleanFilter(label='Featured products')
    in_stock = django_filters.BooleanFilter(
        method='filter_in_stock',
        label='Only products with at least one active variant in stock',
    )

    class Meta:
        model = Product
        fields = ['featured', 'collections', 'category', 'in_stock']

    def filter_in_stock(self, queryset, name, value):
        # Uses Exists() rather than queryset.filter(variants__stock__gt=0),
        # which would JOIN the variants table into the main query and
        # duplicate rows for products with multiple matching variants — that
        # fan-out would corrupt the avg_rating / review_count aggregates
        # annotated in get_queryset(). Exists() is a correlated subquery, so
        # it never adds rows to the outer query.
        in_stock_variant = ProductVariant.objects.filter(
            product=OuterRef('pk'),
            is_active=True,
            stock__gt=0,
        )
        if value:
            return queryset.filter(Exists(in_stock_variant))
        return queryset.exclude(Exists(in_stock_variant))


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]

    queryset = Product.objects.filter(status='active')
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, AliasingOrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['title', 'slug', 'short_description']
    # Real queryset/annotation field names that are valid to order by.
    ordering_fields = ['created_at', 'published_at', 'title', 'min_price']
    # Public API param name -> real field name. Lets clients use the friendly
    # `?ordering=price` / `?ordering=-price` instead of the internal
    # `min_price` annotation name. See AliasingOrderingFilter above.
    ordering_param_aliases = {'price': 'min_price'}
    # Always applied first, before whatever the client asked for (or the
    # default below): products with no active variant (has_variants=False)
    # sort after products with at least one, in every ordering and on every
    # page. See AliasingOrderingFilter.
    ordering_priority_fields = ['-has_variants']
    ordering = ['-published_at', '-id']
    lookup_field = 'slug'
    tags = ['Products']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductListSerializer

    def get_queryset(self):
        # Price doesn't live on Product — each ProductVariant has its own
        # price. "Availability" doesn't either — it depends on whether a
        # product has any active variant at all. Both are computed with
        # correlated Subquery/Exists expressions bound to OuterRef('pk'),
        # rather than as extra .filter()/Min() joins in the same
        # .annotate() call as the review aggregates below. Joining the
        # variants table directly into this query would duplicate rows
        # (fan-out) for products with multiple variants and corrupt
        # avg_rating / review_count. Subquery/Exists are fully isolated and
        # don't have that problem.
        active_variants_qs = ProductVariant.objects.filter(product=OuterRef('pk'), is_active=True)
        min_price_subquery = active_variants_qs.order_by('price').values('price')[:1]

        return (
            Product.objects.select_related('category')
            .prefetch_related(
                Prefetch(
                    'variants',
                    queryset=ProductVariant.objects.filter(is_active=True).select_related('size'),
                    to_attr='active_variants',
                ),
                Prefetch(
                    'images',
                    queryset=ProductImage.objects.filter(media_kind='gallery'),
                    to_attr='gallery_images',
                ),
            )
            .annotate(
                avg_rating=Avg(
                    'reviews__rating',
                    filter=Q(reviews__status=ReviewStatus.APPROVED),
                ),
                review_count=Count(
                    'reviews',
                    filter=Q(reviews__status=ReviewStatus.APPROVED),
                ),
                min_price=Subquery(min_price_subquery),
                has_variants=Exists(active_variants_qs),
            )
            .distinct()
        )

    @extend_schema(
        tags=['Products'],
        parameters=[
            OpenApiParameter(
                name='ordering',
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    'Order results by one of the following fields (prefix with `-` '
                    'for descending order, e.g. `-price`):\n\n'
                    '- `created_at` — product creation date\n'
                    '- `published_at` — product publish date (default ordering)\n'
                    '- `title` — product title (alphabetical)\n'
                    "- `price` — lowest price among the product's **active** "
                    'variants. Price is not stored on the product itself but on '
                    'each variant, so this orders by `MIN(price)` across the '
                    "product's active variants.\n\n"
                    'Regardless of which field/direction you choose, products with '
                    '**no active variant** always sort after every product that has '
                    'one — consistently across pages, not just within a single page. '
                    'A `-id` tie-breaker is also applied automatically so pagination '
                    'stays stable even when many products tie on the chosen field.\n\n'
                    'Example: `?ordering=-price` or `?ordering=created_at,-title`'
                ),
            ),
            OpenApiParameter(
                name='in_stock',
                type=bool,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    'Filter by stock availability. `true` returns only products with '
                    'at least one active variant whose stock is greater than 0. '
                    '`false` returns only products with no such variant.'
                ),
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        """Return a paginated list of active products (status='active').

        Searchable by title/slug/short description (`search`) and filterable
        by category, collection, featured status, and stock availability
        (`in_stock`). See the `ordering` parameter for sorting options and how
        products without variants are always placed at the end.
        """
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=['Products'])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(tags=['Products'], responses=ReviewReadSerializer(many=True))
    @action(detail=True, methods=['get'], url_path='reviews', pagination_class=StandardPagination)
    def reviews(self, request, slug=None):
        product = self.get_object()

        qs = Review.objects.filter(product=product).select_related('user', 'product')

        user = request.user
        if user.is_authenticated and user.is_staff:
            pass
        elif user.is_authenticated:
            qs = qs.filter(Q(status=ReviewStatus.APPROVED) | Q(user=user))
        else:
            qs = qs.filter(status=ReviewStatus.APPROVED)

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = ReviewReadSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = ReviewReadSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)
