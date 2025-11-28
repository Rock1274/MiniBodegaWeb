// Variables globales para el slider
let slider, items, next, prev, dots, lengthItems, active, refreshInterval;

// Función para inicializar el slider de bienvenida
function initWelcomeSlider() {
    slider = document.querySelector('.slider .list');
    items = document.querySelectorAll('.slider .list .item');
    next = document.getElementById('next');
    prev = document.getElementById('prev');
    dots = document.querySelectorAll('.slider .dots li');

    // Verificar que todos los elementos existen
    if (!slider || !items.length || !next || !prev || !dots.length) {
        console.warn('Elementos del slider no encontrados');
        return;
    }

    lengthItems = items.length - 1;
    active = 0;
    
    // Función para recargar el slider
    function reloadSlider(){
        if (slider && items[active]) {
            slider.style.left = -items[active].offsetLeft + 'px';
        }
        
        let last_active_dot = document.querySelector('.slider .dots li.active');
        if (last_active_dot) {
            last_active_dot.classList.remove('active');
        }
        if (dots[active]) {
            dots[active].classList.add('active');
        }

        // Limpiar intervalo anterior y crear uno nuevo
        if (refreshInterval) {
            clearInterval(refreshInterval);
        }
        refreshInterval = setInterval(()=> {
            if (next && next.click) {
                next.click();
            }
        }, 3000);
    }
    
    // Configurar botones
    next.onclick = function(){
        active = active + 1 <= lengthItems ? active + 1 : 0;
        reloadSlider();
    }
    prev.onclick = function(){
        active = active - 1 >= 0 ? active - 1 : lengthItems;
        reloadSlider();
    }
    
    // Configurar dots
    dots.forEach((li, key) => {
        li.addEventListener('click', ()=>{
             active = key;
             reloadSlider();
        });
    });
    
    // Inicializar el slider
    reloadSlider();
    
    console.log('✅ Slider de bienvenida inicializado correctamente');
}

// Inicialización cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    if (document.querySelector('.slider')) {
        initWelcomeSlider();
    }
});

// También inicializar cuando se cargue contenido via AJAX
window.addEventListener('contentLoaded', function(e) {
    if (document.querySelector('.slider')) {
        console.log('Reinicializando slider después de carga AJAX...');
        initWelcomeSlider();
    }
});


