# -*- coding: utf-8 -*-
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models_alertas import PerfilUsuario, AlertaUsuario, CategoriaAlerta

class RegistroUsuarioForm(UserCreationForm):
    """
    Formulario para registro de nuevos usuarios
    """
    email = forms.EmailField(required=True)
    first_name = forms.CharField(label="Nombre", max_length=100, required=True)
    last_name = forms.CharField(label="Apellidos", max_length=100, required=True)
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')
    
    def save(self, commit=True):
        user = super(RegistroUsuarioForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            # Crear perfil de usuario
            PerfilUsuario.objects.create(usuario=user)
        
        return user

class LoginForm(AuthenticationForm):
    """
    Formulario para inicio de sesión
    """
    username = forms.CharField(label="Usuario", max_length=100, required=True)
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput, required=True)

class PerfilUsuarioForm(forms.ModelForm):
    """
    Formulario para editar el perfil de usuario
    """
    class Meta:
        model = PerfilUsuario
        fields = ('telefono', 'organizacion', 'cargo', 'sector', 'recibir_alertas_email')
        labels = {
            'telefono': 'Teléfono',
            'organizacion': 'Organización',
            'cargo': 'Cargo',
            'sector': 'Sector',
            'recibir_alertas_email': 'Recibir alertas por email'
        }

class AlertaUsuarioForm(forms.ModelForm):
    """
    Formulario para crear y editar alertas
    """
    class Meta:
        model = AlertaUsuario
        fields = ('nombre', 'palabras_clave', 'categorias', 'departamentos', 'activa', 'frecuencia', 'umbral_relevancia')
        labels = {
            'nombre': 'Nombre de la alerta',
            'palabras_clave': 'Palabras clave',
            'categorias': 'Categorías',
            'departamentos': 'Departamentos',
            'activa': 'Activa',
            'frecuencia': 'Frecuencia',
            'umbral_relevancia': 'Umbral de relevancia'
        }
        widgets = {
            'palabras_clave': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Ej: contratación, subvenciones, fiscal'}),
            'departamentos': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Ej: Hacienda, Trabajo, Economía'}),
            'umbral_relevancia': forms.NumberInput(attrs={'min': 0, 'max': 1, 'step': 0.1})
        }
        help_texts = {
            'palabras_clave': 'Introduce las palabras clave separadas por comas',
            'departamentos': 'Introduce los departamentos separados por comas',
            'frecuencia': 'Selecciona la frecuencia con la que quieres recibir alertas',
            'umbral_relevancia': 'Valor entre 0 y 1. Cuanto más alto, más relevantes serán las alertas'
        }
