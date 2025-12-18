import logging
from django.core.cache import cache
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)
CACHE_TTL = getattr(settings, 'CACHE_TTL', 300)

class CacheResponseMixin:
    cache_key_prefix = None

    def get_cache_key_prefix(self):
        if self.cache_key_prefix is None:
            return self.__class__.__name__.lower().replace('viewset', '')
        return self.cache_key_prefix

    def list(self, request, *args, **kwargs):
        prefix = self.get_cache_key_prefix()
        cache_key = f"all_{prefix}s"
        data = cache.get(cache_key)

        if not data:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True)
            data = serializer.data
            cache.set(cache_key, data, timeout=CACHE_TTL)
            logger.debug("%s.list cache miss; cached %d records", prefix, len(data))
        else:
            logger.debug("%s.list cache hit", prefix)

        return Response(data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None, *args, **kwargs):
        prefix = self.get_cache_key_prefix()
        cache_key = f"{prefix}_{pk}"
        data = cache.get(cache_key)

        if not data:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            data = serializer.data
            cache.set(cache_key, data, timeout=CACHE_TTL)
            logger.debug("%s.retrieve cache miss for id=%s", prefix, pk)
        else:
            logger.debug("%s.retrieve cache hit for id=%s", prefix, pk)

        return Response(data, status=status.HTTP_200_OK)

class CacheInvalidationMixin:
    def get_cache_keys_to_invalidate(self, instance):
        return []

    def perform_create(self, serializer):
        instance = serializer.save()
        self._invalidate_cache(instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        self._invalidate_cache(instance)

    def perform_destroy(self, instance):
        self._invalidate_cache(instance)
        instance.delete()

    def _invalidate_cache(self, instance):
        keys = self.get_cache_keys_to_invalidate(instance)
        if keys:
            for key in keys:
                cache.delete(key)
            logger.debug("Invalidated cache keys: %s", keys)
