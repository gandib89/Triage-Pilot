from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TicketViewSet, DecisionLogViewSet

router = DefaultRouter()
router.register(r'tickets', TicketViewSet)
router.register(r'decisions', DecisionLogViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
