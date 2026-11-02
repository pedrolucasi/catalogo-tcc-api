from rest_framework.pagination import PageNumberPagination


class PaginacaoPadrao(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'tamanho'
    max_page_size = 50
