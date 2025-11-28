// Función para manejar la vista previa de imágenes
function setupImagePreview() {
    const imageInputs = document.querySelectorAll('input[type="file"][accept="image/*"]');
    
    imageInputs.forEach(input => {
        input.addEventListener('change', function(e) {
            const file = e.target.files[0];
            const previewContainer = document.getElementById('preview-container');
            const imagePreview = document.getElementById('image-preview');
            const imageInfo = document.getElementById('image-info');
            
            if (file) {
                // Validar tipo de archivo
                if (!file.type.startsWith('image/')) {
                    alert('Por favor selecciona un archivo de imagen válido.');
                    input.value = '';
                    return;
                }
                
                // Validar tamaño (máximo 5MB)
                const maxSize = 5 * 1024 * 1024; // 5MB
                if (file.size > maxSize) {
                    alert('La imagen es demasiado grande. El tamaño máximo es 5MB.');
                    input.value = '';
                    return;
                }
                
                // Crear URL para vista previa
                const reader = new FileReader();
                reader.onload = function(e) {
                    imagePreview.src = e.target.result;
                    previewContainer.style.display = 'block';
                    
                    // Mostrar información de la imagen
                    const sizeInMB = (file.size / (1024 * 1024)).toFixed(2);
                    const truncatedName = file.name.length > 30 ? file.name.substring(0, 30) + '...' : file.name;
                    const dimensions = new Image();
                    dimensions.onload = function() {
                        imageInfo.innerHTML = `${truncatedName}<br>${sizeInMB}MB<br>${this.width} × ${this.height}px`;
                    };
                    dimensions.src = e.target.result;
                };
                reader.readAsDataURL(file);
            } else {
                previewContainer.style.display = 'none';
            }
        });
    });
}

// Función para limpiar la vista previa cuando se cierra el modal
function clearImagePreview() {
    const previewContainer = document.getElementById('preview-container');
    const imagePreview = document.getElementById('image-preview');
    const imageInfo = document.getElementById('image-info');
    
    if (previewContainer) {
        previewContainer.style.display = 'none';
    }
    if (imagePreview) {
        imagePreview.src = '';
    }
    if (imageInfo) {
        imageInfo.textContent = '';
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    setupImagePreview();
    
    // Limpiar vista previa cuando se cierre un modal
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.addEventListener('hidden.bs.modal', function() {
            clearImagePreview();
        });
    });
});

// Reinicializar después de carga AJAX
window.addEventListener('contentLoaded', function() {
    setupImagePreview();
}); 