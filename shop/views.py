from django.conf import settings
from django.core.mail import send_mail

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import viewsets, permissions, filters, status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import Category, Product, Order, Review

from .serializers import (
    CategorySerializer,
    ProductSerializer,
    OrderSerializer,
    ReviewSerializer,
    Register,
    LoginSerialiser
)

from .permissions import (
    IsAdminOrReadOnly,
    IsOwnerOrReadOnly
)

from .filters import ProductFilter


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]

    filterset_class = ProductFilter

    search_fields = [
        'title',
        'description'
    ]

    ordering_fields = [
        'price',
        'created_at'
    ]


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer

    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsOwnerOrReadOnly
    ]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [
        permissions.IsAuthenticated
    ]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Order.objects.all()

        return Order.objects.filter(
            user=self.request.user
        )

    def perform_create(self, serializer):
        order = serializer.save(
            user=self.request.user
        )

        if self.request.user.email:
            send_mail(
                subject=f'Заказ #{order.id} оформлен',
                message=(
                    f'Здравствуйте, '
                    f'{self.request.user.username}!\n\n'
                    f'Ваш заказ на сумму '
                    f'{order.total_price} сом '
                    f'успешно оформлен.'
                ),
                from_email=getattr(
                    settings,
                    'DEFAULT_FROM_EMAIL',
                    'noreply@shop.com'
                ),
                recipient_list=[
                    self.request.user.email
                ],
                fail_silently=True
            )


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register(request):
    serializer = Register(
        data=request.data
    )

    if serializer.is_valid():
        user = serializer.save()

        return Response(
            {
                'message': 'Registration successful',
                'username': user.username
            },
            status=status.HTTP_201_CREATED
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login(request):
    serializer = LoginSerialiser(
        data=request.data
    )

    if serializer.is_valid():
        user = serializer.validated_data['user']

        token, created = Token.objects.get_or_create(
            user=user
        )

        return Response(
            {
                'message': 'Login successful',
                'token': token.key
            },
            status=status.HTTP_200_OK
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout(request):
    Token.objects.filter(
        user=request.user
    ).delete()

    return Response(
        {
            'message': 'Logout successful'
        },
        status=status.HTTP_200_OK
    )