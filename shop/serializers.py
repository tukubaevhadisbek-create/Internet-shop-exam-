from django.contrib.auth import get_user_model, authenticate
from django.db import transaction
from rest_framework import serializers

from .models import Category, Product, Order, OrderItem, Review


User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(
        source='category.name'
    )

    class Meta:
        model = Product
        fields = '__all__'


class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(
        source='user.username'
    )

    class Meta:
        model = Review
        fields = '__all__'
        read_only_fields = [
            'user',
            'created_at'
        ]

    def validate(self, data):
        request = self.context.get('request')
        product = data.get('product')

        if (
            request
            and request.user.is_authenticated
            and not self.instance
            and Review.objects.filter(
                user=request.user,
                product=product
            ).exists()
        ):
            raise serializers.ValidationError(
                'Вы уже оставили отзыв на этот товар.'
            )

        return data


class OrderItemSerializer(serializers.ModelSerializer):
    product_title = serializers.ReadOnlyField(
        source='product.title'
    )

    quantity = serializers.IntegerField(
        min_value=1
    )

    class Meta:
        model = OrderItem
        fields = [
            'id',
            'product',
            'product_title',
            'quantity',
            'price'
        ]

        read_only_fields = [
            'id',
            'product_title',
            'price'
        ]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(
        many=True
    )

    user = serializers.ReadOnlyField(
        source='user.username'
    )

    class Meta:
        model = Order

        fields = [
            'id',
            'user',
            'status',
            'total_price',
            'address',
            'created_at',
            'items'
        ]

        read_only_fields = [
            'id',
            'user',
            'status',
            'total_price',
            'created_at'
        ]

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError(
                'Заказ должен содержать хотя бы один товар.'
            )

        return value

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')

        order = Order.objects.create(
            **validated_data
        )

        total = 0

        for item_data in items_data:
            product = Product.objects.select_for_update().get(
                pk=item_data['product'].pk
            )

            quantity = item_data['quantity']

            if product.stock < quantity:
                raise serializers.ValidationError(
                    {
                        'items': (
                            f'Недостаточно товара '
                            f'"{product.title}". '
                            f'На складе: {product.stock}'
                        )
                    }
                )

            price = product.price

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                price=price
            )

            product.stock -= quantity

            product.save(
                update_fields=['stock']
            )

            total += price * quantity

        order.total_price = total

        order.save(
            update_fields=['total_price']
        )

        return order


class Register(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8
    )

    class Meta:
        model = User

        fields = [
            'username',
            'email',
            'password'
        ]

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )


class LoginSerialiser(serializers.Serializer):
    username = serializers.CharField(
        max_length=150
    )

    password = serializers.CharField(
        write_only=True
    )

    def validate(self, data):
        user = authenticate(
            username=data['username'],
            password=data['password']
        )

        if user is None:
            raise serializers.ValidationError(
                'Неверное имя пользователя или пароль.'
            )

        data['user'] = user

        return data