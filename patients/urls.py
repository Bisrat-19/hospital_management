from django.urls import path
from . import views

urlpatterns = [
    path('', views.list_patients_view, name='list-patients'),
    path('register/', views.register_patient_view, name='register-patient'),
    path('<int:pk>/', views.get_patient_view, name='get-patient'),
    path('<int:pk>/update/', views.update_patient_view, name='update-patient'),
    path('<int:pk>/delete/', views.delete_patient_view, name='delete-patient'),
]
