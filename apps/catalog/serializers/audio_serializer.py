from rest_framework import serializers

from ..models.audio_model import Audio


class AudioSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    cover = serializers.SerializerMethodField()

    class Meta:
        model = Audio
        fields = (
            'id',
            'title',
            'artist',
            'url',
            'cover',
        )

    def get_url(self, obj):
        request = self.context.get('request')

        if request:
            return request.build_absolute_uri(obj.audio.url)

        return obj.audio.url

    def get_cover(self, obj):
        request = self.context.get('request')

        if request:
            return request.build_absolute_uri(obj.cover.url)

        return obj.cover.url
