"""
URL configuration for hospital_sys project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from rest_framework.routers import DefaultRouter
from drugs.views import (
    DrugViewSet,
    MedicationRecordViewSet,
    InventoryAdjustmentViewSet,
    OperationLogViewSet,
    AuthViewSet,
    UserViewSet,
    DashboardViewSet,
)

# 创建路由器并注册视图集
router = DefaultRouter()
router.register(r'drugs', DrugViewSet, basename='drug')
router.register(r'medication-records', MedicationRecordViewSet, basename='medication-record')
router.register(r'inventory-adjustments', InventoryAdjustmentViewSet, basename='inventory-adjustment')
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'users', UserViewSet, basename='user')
router.register(r'dashboard', DashboardViewSet, basename='dashboard')
router.register(r'operation-logs', OperationLogViewSet, basename='operation-log')

# 根路径视图
def api_root(request):
    return JsonResponse({
        'message': 'Hospital Management System API',
        'version': '1.0',
        'endpoints': {
            'admin': '/admin/',
            'api_root': '/api/',
            'drugs': '/api/drugs/',
            'medication_records': '/api/medication-records/',
            'auth_login': '/api/auth/login/',
            'auth_logout': '/api/auth/logout/',
            'auth_register': '/api/auth/register/',
            'users': '/api/users/',
            'drugs_warnings': '/api/drugs/warnings/',
            'drugs_stock_in': '/api/drugs/{id}/stock-in/',
            'dashboard': '/api/dashboard/',
            'dashboard_trends': '/api/dashboard/trends/',
            'inventory_adjustments': '/api/inventory-adjustments/',
            'medication_cancel': '/api/medication-records/{id}/cancel/',
            'operation_logs': '/api/operation-logs/',
            'dashboard_recommendations': '/api/dashboard/recommendations/',
            'drug_stock_trend': '/api/drugs/{id}/stock-trend/',
        }
    })

urlpatterns = [
    path("", api_root, name='api-root'),
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
]
