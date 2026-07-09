from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings

from apps.accounts.models import Province, City

import json



class Command(BaseCommand):
    help = 'Import provinces and cities'

    @transaction.atomic
    def handle(self, *args, **options):
        location_dir = settings.BASE_DIR / 'assets/locations'

        provinces_file = location_dir / 'provinces.json'
        cities_file = location_dir / 'cities.json'

        with open(provinces_file, encoding='utf-8') as f:
            provinces_data = json.load(f)

        with open(cities_file, encoding='utf-8') as f:
            cities_data = json.load(f)

        self.stdout.write('Importing provinces...')

        province_map = {}

        for item in provinces_data:
            province, _ = Province.objects.update_or_create(
                id=item['id'],
                defaults={
                    'name': item['name'],
                },
            )

            province_map[province.id] = province

        self.stdout.write(
            self.style.SUCCESS(
                f'{len(province_map)} provinces imported.'
            )
        )

        self.stdout.write('Importing cities...')

        cities = []

        for item in cities_data:
            province = province_map.get(item['ostan'])

            if not province:
                self.stdout.write(
                    self.style.WARNING(
                        f"Province {item['ostan']} not found."
                    )
                )
                continue

            cities.append(
                City(
                    id=item['id'],
                    name=item['name'],
                    province=province,
                )
            )

        City.objects.bulk_create(
            cities,
            ignore_conflicts=True,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'{len(cities)} cities imported.'
            )
        )

        self.stdout.write(
            self.style.SUCCESS('Import completed.')
        )