from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiParameter,
    OpenApiTypes,
)

from rest_framework import (
    viewsets,
    mixins,
    status,
    )

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from core.models import (
    Tag,
    Recipe,
    )

from recipe import serializers

class RecipeViewSet(viewsets.ModelViewSet):

    serializer_class = serializers.RecipeDetailSerializer
    queryset = Recipe.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def _params_to_ints(self, qs):
        return [int(str_id) for str_id in qs.split(',')]


    def get_queryset(self):

        tags = self.request.query_params.get('tags')
        queryset = self.queryset

        if tags:
            tag_ids = self._params_to_ints(tags)
            queryset = queryset.filter(tags__id__in=tag_ids)


        return queryset.filter(user=self.request.user).order_by('-id').distinct()


    def get_serializer_class(self):

        if self.action == 'list':
            return serializers.RecipeSerializer
        elif self.action == 'upload_image':
            return serializers.RecipeImageSerializer

        return self.serializer_class

    def perform_create(self, serializer):

        serializer.save(user= self.request.user)

    @action(methods=['POST'], detail=True, url_path = 'uploa-dimage')
    def upload_image(self, request, pk= None):

        recipe = self.get_object()
        serializer = self.get_serializer(recipe, data=request.data)

        if serializer.is_valid():

            serializer.save()
            return Response(serializer.data, status= status.HTTP_200_OK)

        return Response(serializer.errors, status= status.HTTP_400_BAD_REQUEST)


class TagViewSet(
    mixins.DestroyModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet):

    serializer_class = serializers.TagSerializer
    queryset = Tag.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]


    def get_queryset(self):

        return self.queryset.filter(user=self.request.user).order_by('-name')