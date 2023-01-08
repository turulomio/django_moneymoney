from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

class PagePaginationWithTotalPages(PageNumberPagination):
    page_size = 10
    max_page_size = 1000000

    def get_paginated_response(self, data):
        return Response({
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'page': self.page.number, 
            'results': data, 
        })
