# Sistema de Navegación AJAX

## Descripción
Este sistema permite que solo el contenido de la página se recargue, manteniendo el sidebar intacto con todas sus animaciones. Esto mejora la experiencia del usuario al hacer la navegación más fluida.

## Archivos Principales

### 1. `static/ajax-navigation.js`
- **Clase AjaxNavigation**: Maneja toda la lógica de navegación AJAX
- **Interceptación de enlaces**: Captura clicks en enlaces del sidebar
- **Manejo de formularios**: Procesa envíos de formularios via AJAX
- **Gestión de historial**: Mantiene el historial del navegador sincronizado
- **Indicadores de carga**: Muestra/oculta indicadores de carga
- **Extracción de contenido**: Extrae automáticamente solo el bloque `.content`

### 2. `static/ajax-loader.css`
- Estilos para el indicador de carga
- Animaciones de transición
- Estilos para mensajes de error

### 3. `templates/base.html`
- Template base principal que incluye sidebar y toda la estructura
- Carga el sistema AJAX automáticamente
- El sistema AJAX extrae solo el contenido del bloque `.content`

## Funcionalidades

### Navegación Automática
- Los enlaces del sidebar se interceptan automáticamente
- Solo se cargan las páginas internas (no enlaces externos)
- El historial del navegador se mantiene sincronizado
- Se extrae automáticamente solo el contenido del bloque `.content`

### Manejo de Formularios
- Los formularios se envían via AJAX automáticamente
- Se excluyen formularios con archivos (`enctype="multipart/form-data"`)
- Se manejan redirecciones automáticamente

### Indicadores Visuales
- **Loader**: Spinner centrado durante la carga
- **Transiciones**: Fade del contenido durante carga
- **Errores**: Mensajes de error con auto-cierre

### Compatibilidad
- Funciona con botones atrás/adelante del navegador
- Mantiene URLs sincronizadas
- Compatible con modales y otros componentes

## Uso

### Para Desarrolladores
1. **Nuevas páginas**: Usar `render_template_ajax()` en lugar de `render_template()`
2. **Templates**: Siempre extender `base.html` normalmente
3. **Formularios**: Funcionan automáticamente, excepto los de archivos
4. **Contenido**: Asegurarse de que el contenido esté dentro del bloque `{% block content %}`

### Estructura de Template
```html
{% extends 'base.html' %}

{% block content %}
    <!-- Tu contenido aquí -->
{% endblock %}
```

### Eventos Disponibles
```javascript
// Escuchar cuando se carga nuevo contenido
window.addEventListener('contentLoaded', function(e) {
    console.log('Nuevo contenido cargado:', e.detail.url);
    // Reinicializar componentes aquí
});
```

## Ventajas

1. **Simplicidad**: Solo un template base (`base.html`)
2. **Rendimiento**: Solo se carga el contenido necesario
3. **UX**: Navegación más fluida sin recargas completas
4. **Animaciones**: El sidebar mantiene sus animaciones intactas
5. **Estado**: Se preserva el estado de componentes del sidebar
6. **SEO**: URLs normales funcionan correctamente

## Consideraciones

- Los formularios con archivos deben usar `enctype="multipart/form-data"`
- Los scripts se ejecutan automáticamente en el nuevo contenido
- El sistema es transparente para el usuario final
- Funciona tanto con JavaScript habilitado como deshabilitado 