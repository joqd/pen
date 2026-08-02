from random import randint

from rest_framework.generics import ListAPIView, get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from ..models.audio_model import Audio
from ..serializers.audio_serializer import AudioSerializer


@extend_schema(tags=['Audio'])
class AudioListView(ListAPIView):
    queryset = Audio.objects.all().order_by('id')
    serializer_class = AudioSerializer


@extend_schema(tags=['Audio'])
class NextAudioView(APIView):
    def get(self, request, pk):
        current = get_object_or_404(Audio, pk=pk)

        next_audio = Audio.objects.filter(id__gt=current.id).order_by('id').first()

        if not next_audio:
            next_audio = Audio.objects.order_by('id').first()

        serializer = AudioSerializer(
            next_audio,
            context={'request': request},
        )

        return Response(serializer.data)


@extend_schema(tags=['Audio'])
class PreviousAudioView(APIView):
    def get(self, request, pk):
        current = get_object_or_404(Audio, pk=pk)

        previous_audio = Audio.objects.filter(id__lt=current.id).order_by('-id').first()

        if not previous_audio:
            previous_audio = Audio.objects.order_by('-id').first()

        serializer = AudioSerializer(
            previous_audio,
            context={'request': request},
        )

        return Response(serializer.data)


@extend_schema(tags=['Audio'])
class RandomAudioView(APIView):
    def get(self, request):
        count = Audio.objects.count()

        if count == 0:
            return Response(status=404)

        audio = Audio.objects.all()[randint(0, count - 1)]

        serializer = AudioSerializer(
            audio,
            context={'request': request},
        )

        return Response(serializer.data)
