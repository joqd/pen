from abc import ABC, abstractmethod

from django.conf import settings

DEFAULT_SITE_URL = getattr(settings, "SITE_URL", "https://starboy.ir")
DEFAULT_SITE_NAME = getattr(settings, "SITE_NAME", "استاربوی")
DEFAULT_CURRENCY = getattr(settings, "SEO_PRICE_CURRENCY", "IRT")
DEFAULT_SOCIAL_LINKS = getattr(settings, "SEO_SOCIAL_LINKS", [])


class BaseSchemaBuilder(ABC):
    def __init__(self, instance=None, request=None):
        self.instance = instance
        self.request = request

    @property
    def site_url(self) -> str:
        return DEFAULT_SITE_URL.rstrip("/")

    @abstractmethod
    def build(self) -> dict:
        ...

    def to_json_ld(self) -> dict:
        return self._clean(self.build())

    def _clean(self, data):
        if isinstance(data, dict):
            cleaned = {k: self._clean(v) for k, v in data.items()}
            return {k: v for k, v in cleaned.items() if v not in (None, "", [], {})}
        if isinstance(data, list):
            cleaned = [self._clean(v) for v in data]
            return [v for v in cleaned if v not in (None, "", [], {})]
        return data

    def absolute_url(self, path: str) -> str:
        if not path:
            return ""
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{self.site_url}{path}"

    def absolute_media_url(self, file_field) -> str | None:
        if not file_field:
            return None
        try:
            url = file_field.url
        except ValueError:
            return None
        if self.request:
            return self.request.build_absolute_uri(url)
        return self.absolute_url(url)


# ============================================================
# Product
# ============================================================


class ProductSchemaBuilder(BaseSchemaBuilder):
    def build(self) -> dict:
        product = self.instance
        return {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": product.title,
            "description": self._description(),
            "url": self.absolute_url(f"/products/{product.slug}"),
            "image": self._gallery_images(),
            "brand": self._brand(),
            "category": product.category.title if product.category_id else None,
            "offers": self._offers(),
            "aggregateRating": self._aggregate_rating(),
        }

    def _description(self) -> str:
        product = self.instance
        return (product.description or product.short_description or "").strip()

    def _brand(self) -> dict:
        brand = getattr(self.instance, "brand", None)
        return {"@type": "Brand", "name": getattr(brand, "name", None) or DEFAULT_SITE_NAME}

    def _active_variants(self) -> list:
        product = self.instance
        if hasattr(product, "active_variants"):
            return list(product.active_variants)
        return list(product.variants.filter(is_active=True).select_related("size"))

    def _gallery_images(self) -> list[str]:
        product = self.instance
        if hasattr(product, "gallery_images"):
            images = list(product.gallery_images)
        else:
            images = list(product.images.filter(media_kind="gallery"))
        images = sorted(images, key=lambda img: (not img.is_primary, img.sort_order))
        return [url for img in images if (url := self.absolute_media_url(img.image))]

    def _offers(self) -> dict | None:
        variants = self._active_variants()
        if not variants:
            return None

        if len(variants) == 1:
            return self._single_offer(variants[0])

        return self._aggregate_offer(variants)

    def _single_offer(self, variant) -> dict:
        return {
            "@type": "Offer",
            "url": self.absolute_url(f"/products/{self.instance.slug}"),
            "priceCurrency": DEFAULT_CURRENCY,
            "price": str(variant.price),
            "availability": self._availability(variant.available_stock > 0),
            "itemCondition": "https://schema.org/NewCondition",
            "sku": variant.sku,
        }

    def _aggregate_offer(self, variants: list) -> dict:
        prices = [v.price for v in variants]
        any_in_stock = any(v.available_stock > 0 for v in variants)
        return {
            "@type": "AggregateOffer",
            "url": self.absolute_url(f"/products/{self.instance.slug}"),
            "priceCurrency": DEFAULT_CURRENCY,
            "lowPrice": str(min(prices)),
            "highPrice": str(max(prices)),
            "offerCount": len(variants),
            "availability": self._availability(any_in_stock),
        }

    @staticmethod
    def _availability(in_stock: bool) -> str:
        return "https://schema.org/InStock" if in_stock else "https://schema.org/OutOfStock"

    def _aggregate_rating(self) -> dict | None:
        avg_rating = getattr(self.instance, "avg_rating", None)
        review_count = getattr(self.instance, "review_count", 0)
        if not review_count or avg_rating is None:
            return None
        return {
            "@type": "AggregateRating",
            "ratingValue": round(avg_rating, 1),
            "reviewCount": review_count,
            "bestRating": "5",
        }


# ============================================================
# Category / Collection
# ============================================================


class BaseCollectionPageSchemaBuilder(BaseSchemaBuilder):
    path_prefix: str

    def build(self) -> dict:
        obj = self.instance
        data = {
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "name": obj.title,
            "description": (obj.description or obj.short_description or "").strip(),
            "url": self.absolute_url(f"{self.path_prefix}/{obj.slug}"),
            "image": self.absolute_media_url(obj.image),
        }
        item_list = self._item_list()
        if item_list:
            data["mainEntity"] = item_list
        return data

    def _item_list(self) -> dict | None:
        products = getattr(self.instance, "seo_products", None)
        if not products:
            return None
        items = [
            {
                "@type": "ListItem",
                "position": i + 1,
                "url": self.absolute_url(f"/products/{p.slug}"),
            }
            for i, p in enumerate(products)
        ]
        return {"@type": "ItemList", "itemListElement": items} if items else None


class CategorySchemaBuilder(BaseCollectionPageSchemaBuilder):
    path_prefix = "/categories"


class CollectionSchemaBuilder(BaseCollectionPageSchemaBuilder):
    path_prefix = "/collections"


# ============================================================
# Blog Post
# ============================================================


class ArticleSchemaBuilder(BaseSchemaBuilder):
    def build(self) -> dict:
        post = self.instance
        return {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": post.title[:110],
            "description": post.excerpt,
            "image": self.absolute_media_url(post.featured_image),
            "datePublished": self._date_published(),
            "dateModified": post.updated_at.isoformat(),
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": self.absolute_url(f"/blog/{post.slug}"),
            },
            "author": self._author(),
            "publisher": self._publisher(),
            "articleSection": post.category.title if post.category_id else None,
        }

    def _date_published(self) -> str:
        post = self.instance
        dt = post.published_at or post.created_at
        return dt.isoformat()

    def _author(self) -> dict:
        author = self.instance.author
        if not author:
            return {"@type": "Organization", "name": DEFAULT_SITE_NAME}
        name = (
            author.get_full_name()
            if hasattr(author, "get_full_name") and author.get_full_name()
            else getattr(author, "username", DEFAULT_SITE_NAME)
        )
        return {"@type": "Person", "name": name}

    def _publisher(self) -> dict:
        return {
            "@type": "Organization",
            "name": DEFAULT_SITE_NAME,
            "logo": {
                "@type": "ImageObject",
                "url": self.absolute_url("/logo.png"),
            },
        }


# ============================================================
# Breadcrumb
# ============================================================


class BreadcrumbSchemaBuilder(BaseSchemaBuilder):
    def __init__(self, items: list[tuple[str, str]], request=None):
        self.items = items
        self.instance = None
        self.request = request

    def build(self) -> dict:
        return {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": i + 1,
                    "name": name,
                    "item": self.absolute_url(path),
                }
                for i, (name, path) in enumerate(self.items)
            ],
        }

    @classmethod
    def for_product(cls, product, request=None) -> "BreadcrumbSchemaBuilder":
        items = [("خانه", "/")]
        items += cls._category_chain(product.category, path_prefix="/categories")
        items.append((product.title, f"/products/{product.slug}"))
        return cls(items, request=request)

    @classmethod
    def for_category(cls, category, request=None) -> "BreadcrumbSchemaBuilder":
        items = [("خانه", "/")]
        items += cls._category_chain(category.parent, path_prefix="/categories")
        items.append((category.title, f"/categories/{category.slug}"))
        return cls(items, request=request)

    @classmethod
    def for_collection(cls, collection, request=None) -> "BreadcrumbSchemaBuilder":
        items = [("خانه", "/")]
        items += cls._category_chain(collection.parent, path_prefix="/collections")
        items.append((collection.title, f"/collections/{collection.slug}"))
        return cls(items, request=request)

    @classmethod
    def for_post(cls, post, request=None) -> "BreadcrumbSchemaBuilder":
        items = [("خانه", "/"), ("بلاگ", "/blog")]
        if post.category_id:
            items.append((post.category.title, f"/blog/category/{post.category.slug}"))
        items.append((post.title, f"/blog/{post.slug}"))
        return cls(items, request=request)

    @staticmethod
    def _category_chain(node, path_prefix: str) -> list[tuple[str, str]]:
        chain = []
        stack = []
        current = node
        while current:
            stack.append(current)
            current = current.parent
        for n in reversed(stack):
            chain.append((n.title, f"{path_prefix}/{n.slug}"))
        return chain


# ============================================================
# Organization / Website
# ============================================================


class OrganizationSchemaBuilder(BaseSchemaBuilder):
    def build(self) -> dict:
        return {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": DEFAULT_SITE_NAME,
            "url": self.site_url,
            "logo": self.absolute_url("/logo.png"),
            "sameAs": DEFAULT_SOCIAL_LINKS,
        }


class WebsiteSchemaBuilder(BaseSchemaBuilder):
    def build(self) -> dict:
        return {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": DEFAULT_SITE_NAME,
            "url": self.site_url,
            "potentialAction": {
                "@type": "SearchAction",
                "target": f"{self.site_url}/search?q={{search_term_string}}",
                "query-input": "required name=search_term_string",
            },
        }