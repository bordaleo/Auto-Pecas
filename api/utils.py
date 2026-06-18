"""Utilitários — AutoPeças Sandroni."""


def is_superadmin(user):
    return user.is_authenticated and (user.is_superuser or user.is_staff)
