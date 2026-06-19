from rest_framework import permissions
from api.models import Seller


class IsActiveSeller(permissions.BasePermission):
    message = 'Você precisa de uma loja ativa na Galelugi para esta ação.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_staff:
            return True
        return Seller.objects.filter(
            user=request.user,
            status=Seller.Status.ACTIVE,
        ).exists()


def get_seller_for_user(user):
    if not user or not user.is_authenticated:
        return None
    try:
        return user.seller_profile
    except Seller.DoesNotExist:
        return None
