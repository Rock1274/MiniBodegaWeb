// Sistema de navegación AJAX para mantener el sidebar intacto
class AjaxNavigation {
    constructor() {
        this.contentContainer = document.querySelector('.content');
        this.currentUrl = window.location.pathname;
        this.init();
    }

    init() {
        // Interceptar clicks en enlaces del sidebar
        this.interceptSidebarLinks();
        this.interceptAllInternalLinks();

        // Manejar navegación del navegador (botones atrás/adelante)
        window.addEventListener('popstate', (e) => {
            this.loadContent(e.state ? e.state.url : '/', false);
        });

        // Interceptar formularios para usar AJAX
        this.interceptForms();
    }

    interceptSidebarLinks() {
        const sidebarLinks = document.querySelectorAll('.sidebar a[href]');

        sidebarLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                const href = link.getAttribute('href');

                // No interceptar enlaces externos, con target="_blank", o rutas específicas como login/logout
                if (href.startsWith('http') || href.startsWith('#') || link.target === '_blank' || href === '/logout' || href === '/login') {
                    return;
                }

                e.preventDefault();
                this.navigateTo(href);
            });
        });
    }

    interceptAllInternalLinks() {
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a[href]');
            if (!link) return;

            const href = link.getAttribute('href');

            // Ignorar externos, con target="_blank", o rutas específicas como login/logout
            if (href.startsWith('http') || link.target === '_blank' || href.startsWith('#') || href === '/logout' || href === '/login') return;

            e.preventDefault();
            this.navigateTo(href);
        });
    }

    interceptForms() {
        document.addEventListener('submit', (e) => {
            const form = e.target;

            if (form.hasAttribute('data-no-ajax')) return;

            if (form.closest('.modal')) return;

            const action = form.action || '';
            if (action.startsWith('http') && !action.includes(window.location.host)) return;

            // No interceptar formularios de login
            if (action.includes('/login')) return;

            e.preventDefault();
            this.submitForm(form);
        });
    }


    navigateTo(url) {
        // Actualizar URL sin recargar la página
        window.history.pushState({ url: url }, '', url);
        this.loadContent(url, true);
    }

    clearContent() {
        console.log('🧹 Limpiando contenido anterior...');

        // Limpiar completamente el contenido anterior
        this.contentContainer.innerHTML = '';
        console.log('✅ Contenido del contenedor limpiado');

        // Limpiar también cualquier script que se haya agregado dinámicamente
        const dynamicScripts = document.querySelectorAll('script[data-dynamic="true"]');
        console.log('🗑️ Removiendo', dynamicScripts.length, 'scripts dinámicos');
        dynamicScripts.forEach(script => script.remove());

        // Limpiar estilos específicos de páginas anteriores
        this.removePreviousPageStyles();

        // LIMPIAR ELEMENTOS DINÁMICOS CON SOMBRAS QUE PUEDEN ACUMULARSE
        // this.clearDynamicShadowElements(); // DESACTIVADO PARA PERMITIR MODAL FADE

        // Forzar un reflow para asegurar que el contenido se limpie completamente
        this.contentContainer.offsetHeight;
        console.log('✅ Limpieza completada');
    }

    clearDynamicShadowElements() {
        // Limpieza silenciosa de elementos dinámicos - DESACTIVADA PARA PERMITIR MODAL FADE
        console.log('🧹 Limpieza de elementos dinámicos DESACTIVADA para permitir modal fade');

        // Solo mantener funcionalidad básica sin eliminar elementos fade
        const logoutModal = document.getElementById('confirmLogoutModal');
        if (logoutModal) {
            console.log('🛡️ Modal de cerrar sesión preservado');
        }

        // CERRAR TODOS LOS OTROS MODALES (excepto el de logout)
        const openModals = document.querySelectorAll('.modal.show');
        openModals.forEach(modal => {
            if (modal.id !== 'confirmLogoutModal') {
                if (typeof bootstrap !== 'undefined') {
                    const bsModal = bootstrap.Modal.getInstance(modal);
                    if (bsModal) {
                        bsModal.hide();
                    } else {
                        modal.classList.remove('show');
                        modal.style.display = 'none';
                    }
                } else {
                    // Fallback si Bootstrap no está disponible
                    modal.classList.remove('show');
                    modal.style.display = 'none';
                }
            }
        });

        // Remover modales de error acumulados
        const errorOverlays = document.querySelectorAll('.error-overlay');
        errorOverlays.forEach(overlay => {
            console.log('🗑️ Removiendo modal de error acumulado');
            overlay.remove();
        });

        // Remover dropdowns/buscadores abiertos
        const dropdowns = document.querySelectorAll('.dropdown-menu.show');
        dropdowns.forEach(dropdown => {
            console.log('🗑️ Cerrando dropdown abierto');
            dropdown.classList.remove('show');
            dropdown.style.display = 'none';
        });

        // Limpiar menús de opciones de empleados que puedan estar abiertos
        const openMenus = document.querySelectorAll('.menu-opciones[style*="display: block"]');
        openMenus.forEach(menu => {
            console.log('🗑️ Cerrando menú de opciones abierto');
            menu.style.display = 'none';
            menu.classList.remove('show');

            // Restaurar el botón correspondiente
            const buttonId = menu.id.replace('menu-', 'btn-');
            const button = document.getElementById(buttonId);
            if (button) {
                button.style.backgroundImage = "url('/static/Iconos_paq/opciones_cn.png')";
                button.style.transform = "scale(1) rotate(0deg)";

                // Quitar color de la fila
                const row = button.closest('tr');
                if (row) {
                    row.classList.remove('fila-activa');
                }
            }
        });

        console.log('✅ Limpieza básica completada - Modal fade preservado');
    }

    clearEmpleadosElements() {
        console.log('🧹 Limpiando elementos específicos de empleados...');

        // Limpiar menús de opciones abiertos
        const openMenus = document.querySelectorAll('.menu-opciones[style*="display: block"]');
        openMenus.forEach(menu => {
            menu.style.display = 'none';
            menu.classList.remove('show');
        });

        // Limpiar filas activas
        const activeRows = document.querySelectorAll('.fila-activa');
        activeRows.forEach(row => {
            row.classList.remove('fila-activa');
        });

        // Limpiar botones con transformaciones
        const transformedButtons = document.querySelectorAll('.botonOpciones[style*="transform"]');
        transformedButtons.forEach(button => {
            button.style.transform = "scale(1) rotate(0deg)";
            button.style.backgroundImage = "url('/static/Iconos_paq/opciones_cn.png')";
        });

        console.log('✅ Limpieza de elementos de empleados completada');
    }

    // Función para obtener estadísticas en tiempo real del sistema de limpieza (modo silencioso)
    getModalCleanupStats() {
        const stats = {
            timestamp: new Date().toISOString(),
            backdrops: document.querySelectorAll('.modal-backdrop').length,
            fadeElements: document.querySelectorAll('.fade:not(.modal)').length,
            totalModals: document.querySelectorAll('.modal').length,
            activeModals: document.querySelectorAll('.modal.show').length,
            logoutModal: !!document.getElementById('confirmLogoutModal'),
            bootstrapAvailable: typeof bootstrap !== 'undefined',
            observersActive: !!(this.bodyObserver && this.documentObserver),
            monitoringActive: !!this.backdropKillerInterval
        };

        return stats;
    }

    async loadContent(url, updateHistory = true) {
        try {
            console.log('🔄 Cargando contenido AJAX para:', url);

            // LIMPIEZA ESPECÍFICA ANTES DE CARGAR NUEVO CONTENIDO
            if (url.includes('empleados')) {
                this.clearEmpleadosElements();
            }
    
            // LIMPIEZA BÁSICA ANTES DE CARGAR NUEVO CONTENIDO
            // this.forceCleanAllShadowElements(); // DESACTIVADO PARA PERMITIR MODAL FADE

            // Ocultar contenido actual durante la carga para evitar FOUC
            this.contentContainer.classList.remove('loaded');

            // Mostrar indicador de carga
            this.showLoading();

            const response = await fetch(url + (url.includes('?') ? '&' : '?') + '_t=' + Date.now(), {
                headers: {
                    'X-Custom-Ajax-Navigation': 'true',
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const contentType = response.headers.get('content-type');
            let data;

            if (contentType && contentType.includes('application/json')) {
                // Respuesta JSON con content y modals
                data = await response.json();
                console.log('📄 Respuesta JSON recibida:', data);
            } else {
                // Respuesta HTML tradicional (fallback)
                const html = await response.text();
                console.log('📄 HTML recibido (primeros 500 caracteres):', html.substring(0, 500));
                data = { content: html, modals: '' };
            }

            // Extraer contenido
            const parser = new DOMParser();
            const contentDoc = parser.parseFromString(data.content, 'text/html');
            const newContent = contentDoc.querySelector('.content') || contentDoc.body;

            console.log('🔍 Contenido encontrado:', newContent ? 'SÍ' : 'NO');
            if (newContent) {
                console.log('📋 Contenido del .content (primeros 300 caracteres):', newContent.innerHTML.substring(0, 300));
            }

            if (newContent) {
                // Pre-cargar estilos específicos antes de mostrar contenido
                await this.preloadPageStyles(url, contentDoc);

                // Limpiar completamente el contenido anterior
                this.clearContent();

                // Cargar estilos específicos de la página
                this.loadPageStyles(contentDoc);

                // Actualizar solo el contenido
                this.contentContainer.innerHTML = newContent.innerHTML;
                console.log('✅ Contenido actualizado en el DOM');

                // Ejecutar scripts del nuevo contenido
                this.executeScripts(newContent);

                // Cargar modales dinámicos si hay datos de modals
                if (data.modals) {
                    this.loadDynamicModalsFromHTML(data.modals);
                }

                // Actualizar título de la página
                const newTitle = contentDoc.querySelector('title');
                if (newTitle) {
                    document.title = newTitle.textContent;
                }

                // Actualizar URL si es necesario
                if (updateHistory) {
                    this.currentUrl = url;
                }

                // Mostrar contenido con transición suave
                setTimeout(() => {
                    this.contentContainer.classList.add('loaded');
                }, 50);

                // Disparar evento personalizado para que otros scripts sepan que el contenido cambió
                window.dispatchEvent(new CustomEvent('contentLoaded', { detail: { url: url } }));

                // Ejecutar funciones específicas según la página
                this.executePageSpecificFunctions(url);

                // Ejecutar prueba de contenido después de un delay
                setTimeout(() => {
                    this.testContentLoading();
                }, 500);
            } else {
                console.warn('⚠️ No se encontró contenido en la respuesta');
                console.log('🔍 Datos recibidos:', data);
            }

        } catch (error) {
            console.error('❌ Error cargando contenido:', error);
            this.showError('Error al cargar la página. Por favor, recarga la página.');
        } finally {
            this.hideLoading();
        }
    }

    async submitForm(form) {
        // LIMPIEZA BÁSICA ANTES DE ENVIAR FORMULARIO
        // this.forceCleanAllShadowElements(); // DESACTIVADO PARA PERMITIR MODAL FADE

        // Ocultar contenido durante el envío del formulario
        this.contentContainer.classList.remove('loaded');
        
        try {
            this.showLoading();

            const formData = new FormData(form);
            const url = form.action || window.location.pathname;
            const method = form.method || 'POST';

            console.log('📤 Iniciando envío de formulario a:', url, 'Método:', method);

            // Si el método es GET, agrega los datos a la URL
            if (method.toLowerCase() === 'get') {
                const params = new URLSearchParams(new FormData(form)).toString();
                const urlWithParams = url + (url.includes('?') ? '&' : '?') + params;
                const response = await fetch(urlWithParams + (urlWithParams.includes('?') ? '&' : '?') + '_t=' + Date.now(), {
                    method: 'GET',
                    headers: {
                        'X-Custom-Ajax-Navigation': 'true',
                        'Cache-Control': 'no-cache, no-store, must-revalidate',
                        'Pragma': 'no-cache'
                    }
                });
                console.log('📤 Respuesta cruda - Status:', response.status, 'OK:', response.ok, 'Redirected:', response.redirected, 'URL:', response.url, 'Content-Type:', response.headers.get('content-type'));

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const contentType = response.headers.get('content-type');
                let data;

                if (contentType && contentType.includes('application/json')) {
                    // Respuesta JSON con content y modals
                    data = await response.json();
                    console.log('📄 Respuesta JSON recibida:', data);
                } else {
                    // Respuesta HTML tradicional (fallback)
                    const html = await response.text();
                    console.log('📄 HTML recibido (primeros 500 caracteres):', html.substring(0, 500));
                    data = { content: html, modals: '' };
                }

                // Buscar redirecciones en el contenido si es HTML
                if (!contentType || !contentType.includes('application/json')) {
                    const redirectMatch = data.content.match(/window\.location\.href\s*=\s*['"]([^'"]+)['"]/);
                    if (redirectMatch) {
                        this.navigateTo(redirectMatch[1]);
                        return;
                    }
                }

                // Extraer contenido
                const parser = new DOMParser();
                const contentDoc = parser.parseFromString(data.content, 'text/html');
                const newContent = contentDoc.querySelector('.content') || contentDoc.body;

                console.log('🔍 Contenido encontrado:', newContent ? 'SÍ' : 'NO');
                if (newContent) {
                    console.log('📋 Contenido del .content (primeros 300 caracteres):', newContent.innerHTML.substring(0, 300));
                }

                if (newContent) {
                    // Pre-cargar estilos específicos antes de mostrar contenido
                    await this.preloadPageStyles(this.currentUrl, contentDoc);

                    // Limpiar completamente el contenido anterior y elementos dinámicos
                    this.clearContent();

                    // Cargar estilos específicos de la página
                    this.loadPageStyles(contentDoc);

                    // Actualizar solo el contenido
                    this.contentContainer.innerHTML = newContent.innerHTML;
                    console.log('✅ Contenido actualizado en el DOM');

                    // Ejecutar scripts del nuevo contenido
                    this.executeScripts(newContent);

                    // Cargar modales dinámicos si hay datos de modals
                    if (data.modals) {
                        this.loadDynamicModalsFromHTML(data.modals);
                    }

                    // Actualizar título de la página
                    const newTitle = contentDoc.querySelector('title');
                    if (newTitle) {
                        document.title = newTitle.textContent;
                    }

                    // Actualizar URL actual
                    this.currentUrl = url;

                    // Mostrar contenido con transición suave
                    setTimeout(() => {
                        this.contentContainer.classList.add('loaded');
                    }, 50);

                    // Disparar evento personalizado para que otros scripts sepan que el contenido cambió
                    window.dispatchEvent(new CustomEvent('contentLoaded', { detail: { url: url } }));

                    // Ejecutar funciones específicas según la página
                    this.executePageSpecificFunctions(url);

                    // Ejecutar prueba de contenido después de un delay
                    setTimeout(() => {
                        this.testContentLoading();
                    }, 500);
                } else {
                    console.warn('⚠️ No se encontró contenido en la respuesta');
                    console.log('🔍 Datos recibidos:', data);
                }
            } else {
                // Para POST, sí puedes usar body
                const response = await fetch(url, {
                    method: method,
                    body: formData,
                    headers: {
                        'X-Custom-Ajax-Navigation': 'true',
                        'Cache-Control': 'no-cache, no-store, must-revalidate',
                        'Pragma': 'no-cache'
                    }
                });

                if (response.headers.get("content-type")?.includes("application/json")) {
                    const data = await response.json();

                    if (data.redirect) {
                        console.log("🔄 Redirección AJAX:", data.redirect);
                        return this.navigateTo(data.redirect);
                    }
                }

                console.log('📤 Respuesta del servidor - Status:', response.status, 'Redirected:', response.redirected, 'URL final:', response.url);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                // Detectar si la respuesta fue redirigida (ej. después de guardar)
                if (response.redirected) {
                    console.log('🔄 Redirección detectada a:', response.url);
                    // Actualizar URL y cargar contenido vía AJAX
                    this.navigateTo(response.url);
                    return;  // Salir sin procesar más
                }


                // Verificar si hay redirección en los headers
                const redirectUrl = response.headers.get('Location');
                if (redirectUrl) {
                    this.navigateTo(redirectUrl);
                    return;
                }

                const html = await response.text();

                let finalHtml = html;
                if (response.headers.get('content-type')?.includes('application/json')) {
                    try {
                        const data = JSON.parse(html);
                        finalHtml = data.html || html;  // Asume que el JSON tiene 'html'
                    } catch (e) {
                        console.warn('⚠️ Respuesta JSON inválida:', e);
                    }
                }


                // Buscar redirecciones en el contenido HTML
                const redirectMatch = html.match(/window\.location\.href\s*=\s*['"]([^'"]+)['"]/);
                if (redirectMatch) {
                    this.navigateTo(redirectMatch[1]);
                    return;
                }

                // Extraer y actualizar contenido
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const newContent = doc.querySelector('.content');

                if (newContent) {
                    // Pre-cargar estilos específicos antes de mostrar contenido
                    await this.preloadPageStyles(this.currentUrl, doc);

                    // Limpiar completamente el contenido anterior y elementos dinámicos
                    this.clearContent();

                    this.contentContainer.innerHTML = newContent.innerHTML;
                    this.executeScripts(newContent);

                    // Actualizar título de la página
                    const newTitle = doc.querySelector('title');
                    if (newTitle) {
                        document.title = newTitle.textContent;
                    }

                    // Mostrar contenido con transición suave
                    setTimeout(() => {
                        this.contentContainer.classList.add('loaded');
                    }, 50);

                    window.dispatchEvent(new CustomEvent('contentLoaded', { detail: { url: this.currentUrl } }));
                } else {
                    // Si no hay contenido, podría ser una redirección
                    console.log('No se encontró contenido en la respuesta');
                }
            }

        } catch (error) {
            console.error('Error enviando formulario:', error);
            this.showError('Error al procesar el formulario. Por favor, intenta de nuevo.');
        } finally {
            this.hideLoading();
        }
    }

    executeScripts(container) {
        // Ejecutar scripts del nuevo contenido
        const scripts = container.querySelectorAll('script');
        scripts.forEach(script => {
            const newScript = document.createElement('script');
            if (script.src) {
                newScript.src = script.src;
                newScript.setAttribute('data-dynamic', 'true');
                // Para scripts externos, esperar a que se carguen
                newScript.onload = () => {
                    console.log('Script externo cargado:', script.src);
                    // Ejecutar scripts que dependen de elementos del DOM después de un pequeño delay
                    setTimeout(() => {
                        this.executeDOMDependentScripts();
                    }, 100);
                };
                document.head.appendChild(newScript);
            } else {
                newScript.textContent = script.textContent;
                newScript.setAttribute('data-dynamic', 'true');
                document.head.appendChild(newScript);
                // Ejecutar inmediatamente scripts inline
                try {
                    eval(script.textContent);
                } catch (error) {
                    console.warn('Error ejecutando script inline:', error);
                }
            }
        });

        // Ejecutar scripts que dependen de elementos del DOM después de un delay
        setTimeout(() => {
            this.executeDOMDependentScripts();
        }, 200);
    }

    executeDOMDependentScripts() {
        // Ejecutar scripts específicos que dependen de elementos del DOM
        console.log('Ejecutando scripts dependientes del DOM...');

        // Disparar evento para que otros scripts sepan que el contenido cambió
        window.dispatchEvent(new CustomEvent('contentLoaded', {
            detail: {
                url: this.currentUrl,
                timestamp: Date.now()
            }
        }));
    }

    showLoading() {
        // Función vacía - no mostrar loader
        // Solo mantener la funcionalidad AJAX sin animación de carga
    }

    hideLoading() {
        // Función vacía - no ocultar loader
        // Solo mantener la funcionalidad AJAX sin animación de carga
    }

    showError(message) {
        // Crear contenedor principal del error
        const errorOverlay = document.createElement('div');
        errorOverlay.className = 'error-overlay';

        // Crear tarjeta de error moderna
        const errorCard = document.createElement('div');
        errorCard.className = 'error-card';

        // Icono de error
        const errorIcon = document.createElement('div');
        errorIcon.className = 'error-icon';
        errorIcon.innerHTML = `
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="12" r="10" stroke="#ef4444" stroke-width="2"/>
                <path d="m15 9-6 6" stroke="#ef4444" stroke-width="2" stroke-linecap="round"/>
                <path d="m9 9 6 6" stroke="#ef4444" stroke-width="2" stroke-linecap="round"/>
            </svg>
        `;

        // Contenido del error
        const errorContent = document.createElement('div');
        errorContent.className = 'error-content';
        errorContent.innerHTML = `
            <h3 class="error-title">¡Oops! Algo salió mal</h3>
            <p class="error-message">${message}</p>
            <div class="error-actions">
                <button class="error-btn error-btn-primary" onclick="window.location.reload()">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        <path d="M21 3v5h-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        <path d="M3 21v-5h5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                    Recargar página
                </button>
                <button class="error-btn error-btn-secondary" onclick="this.closest('.error-overlay').remove()">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M18 6L6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        <path d="M6 6l12 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                    Cerrar
                </button>
            </div>
        `;

        // Ensamblar la tarjeta
        errorCard.appendChild(errorIcon);
        errorCard.appendChild(errorContent);
        errorOverlay.appendChild(errorCard);

        // Agregar al DOM
        document.body.appendChild(errorOverlay);

        // Animación de entrada
        setTimeout(() => {
            errorOverlay.classList.add('show');
        }, 10);

        // Auto-remover después de 8 segundos
        setTimeout(() => {
            if (errorOverlay.parentElement) {
                errorOverlay.classList.remove('show');
                setTimeout(() => {
                    if (errorOverlay.parentElement) {
                        errorOverlay.remove();
                    }
                }, 300);
            }
        }, 8000);
    }

    async preloadPageStyles(url, doc) {
        console.log('🎨 Verificando si se necesitan estilos específicos para:', url);

        // Detectar páginas que necesitan estilos específicos
        const needsPreload = this.needsStylePreload(url);

        if (needsPreload) {
            console.log('📥 Precargando estilos para:', url);

            // Crear una promesa que se resuelva cuando los estilos estén listos
            return new Promise((resolve) => {
                const stylePath = this.getStylePathForPage(url);

                if (stylePath) {
                    // Crear elemento de preload
                    const preloadLink = document.createElement('link');
                    preloadLink.rel = 'preload';
                    preloadLink.href = stylePath;
                    preloadLink.as = 'style';
                    preloadLink.onload = () => {
                        console.log('✅ Estilos precargados para:', url);
                        // Convertir a stylesheet
                        preloadLink.onload = null;
                        preloadLink.rel = 'stylesheet';
                        resolve();
                    };
                    preloadLink.onerror = () => {
                        console.warn('⚠️ Error precargando estilos para:', url);
                        resolve(); // Resolver de todos modos para no bloquear
                    };

                    document.head.appendChild(preloadLink);
                } else {
                    resolve();
                }
            });
        } else {
            console.log('ℹ️ No se necesitan estilos específicos para:', url);
            return Promise.resolve();
        }
    }

    needsStylePreload(url) {
        // Detectar páginas que necesitan preload de estilos
        return url.includes('bienvenida') ||
                url === '/' ||
                url.includes('paquetes') ||
                url.includes('empleados') ||
                url.includes('crear') ||
                url.includes('editar');
    }

    getStylePathForPage(url) {
        // Mapear URLs a rutas de estilos específicos
        if (url.includes('bienvenida') || url === '/') {
            return '/static/CSS Bienvenida/style_Bienvenida.css';
        }
        // Agregar más mappings según sea necesario
        return null;
    }

    loadPageStyles(doc) {
        // Remover estilos específicos de páginas anteriores
        this.removePreviousPageStyles();

        // Buscar y cargar estilos específicos de la página
        const styles = doc.querySelectorAll('link[rel="stylesheet"]');
        styles.forEach(style => {
            const href = style.getAttribute('href');
            if (href && !this.isStyleAlreadyLoaded(href)) {
                console.log('Cargando estilo:', href);
                this.loadStyle(href);
            }
        });

        // Buscar y aplicar estilos inline
        const inlineStyles = doc.querySelectorAll('style');
        inlineStyles.forEach(style => {
            if (!this.isInlineStyleAlreadyLoaded(style.textContent)) {
                console.log('Cargando estilo inline');
                this.loadInlineStyle(style.textContent);
            }
        });
    }

    removePreviousPageStyles() {
        // Remover estilos específicos de páginas anteriores
        const pageStyles = document.querySelectorAll('link[data-page-style="true"]');
        pageStyles.forEach(style => {
            style.remove();
        });

        const pageInlineStyles = document.querySelectorAll('style[data-page-style="true"]');
        pageInlineStyles.forEach(style => {
            style.remove();
        });
    }

    isStyleAlreadyLoaded(href) {
        return document.querySelector(`link[href="${href}"]`) !== null;
    }

    isInlineStyleAlreadyLoaded(content) {
        const existingStyles = document.querySelectorAll('style[data-page-style="true"]');
        for (let style of existingStyles) {
            if (style.textContent === content) {
                return true;
            }
        }
        return false;
    }

    loadStyle(href) {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = href;
        link.setAttribute('data-page-style', 'true');

        // Cargar el estilo de forma asíncrona para evitar bloqueos
        link.onload = () => {
            console.log('Estilo cargado exitosamente:', href);
        };

        link.onerror = () => {
            console.warn('Error cargando estilo:', href);
        };

        document.head.appendChild(link);
    }

    loadInlineStyle(content) {
        const style = document.createElement('style');
        style.textContent = content;
        style.setAttribute('data-page-style', 'true');
        document.head.appendChild(style);
    }

    executePageSpecificFunctions(url) {
        // Ejecutar funciones específicas según la página
        console.log('Ejecutando funciones específicas según la página:', url);

        if (url.includes('bienvenida') || url === '/') {
            this.executeBienvenidaFunctions();
        }

        if (url.includes('paquetes')) {
            this.executePaquetesFunctions();
        }

        if (url.includes('empleados')) {
            this.executeEmpleadosFunctions();
        }
    }

    executeBienvenidaFunctions() {
        console.log('Ejecutando funciones específicas de bienvenida');

        // Remover clase de loading del slider
        const slider = document.querySelector('.slider');
        if (slider) {
            slider.classList.remove('loading');
        }
    }

    executePaquetesFunctions() {
        console.log('Ejecutando funciones específicas de paquetes');

        // Asegurar que los efectos de las cards funcionen
        setTimeout(() => {
            const cards = document.querySelectorAll('.zoom-card');
            cards.forEach(card => {
                card.offsetHeight; // Trigger reflow
            });
        }, 100);
    }

    executeEmpleadosFunctions() {
        console.log('Ejecutando funciones específicas de empleados');

        // LIMPIEZA COMPLETA ANTES DE REINICIALIZAR
        setTimeout(() => {
            // 1. Limpiar event listeners existentes completamente
            const existingButtons = document.querySelectorAll('.botonOpciones');
            existingButtons.forEach(button => {
                // Crear nuevo botón sin event listeners
                const newButton = button.cloneNode(true);
                button.parentNode.replaceChild(newButton, button);
            });

            // 2. Limpiar variables globales anteriores completamente
            delete window.opcionesIcon;
            delete window.opcionesAbiertoIcon;
            delete window.menuHandlersInitialized;

            // 3. Limpiar menús abiertos
            const openMenus = document.querySelectorAll('.menu-opciones.show');
            openMenus.forEach(menu => {
                menu.classList.remove('show');
                menu.style.display = 'none';
            });

            // 4. Limpiar filas activas
            const activeRows = document.querySelectorAll('.fila-activa');
            activeRows.forEach(row => {
                row.classList.remove('fila-activa');
            });

            // 5. Limpiar event listeners del documento
            const oldListeners = document.querySelectorAll('[data-menu-listener]');
            oldListeners.forEach(el => {
                el.removeAttribute('data-menu-listener');
            });

            // 6. Definir variables globales correctamente
            window.opcionesIcon = "/static/Iconos_paq/opciones_cn.png";
            window.opcionesAbiertoIcon = "/static/Iconos_paq/opciones_sc.png";

            // 7. Configurar delegación de eventos
            document.addEventListener('click', function(event) {
                const button = event.target.closest('.botonOpciones');
                if (button && button.hasAttribute('data-menu-id')) {
                    event.stopPropagation();
                    const menuId = button.getAttribute('data-menu-id');
                    const btnId = button.getAttribute('data-btn-id');
                    if (menuId && btnId) {
                        // Usar la función toggleMenu del template
                        if (typeof window.toggleMenuEmpleados === 'function') {
                            window.toggleMenuEmpleados(menuId, btnId);
                        }
                    }
                }
            });
            document.body.setAttribute('data-menu-listener', 'true');

            // 8. Marcar como inicializado
            window.menuHandlersInitialized = true;

            console.log('✅ Funciones específicas de empleados ejecutadas correctamente');
        }, 300); // Aumentar delay para asegurar que el DOM esté completamente listo
    }

    // Función de prueba para verificar el contenido
    testContentLoading() {
        console.log('🧪 Iniciando prueba de carga de contenido...');
        console.log('📍 URL actual:', this.currentUrl);
        console.log('📦 Contenedor de contenido:', this.contentContainer);
        console.log('📋 Contenido actual del contenedor:', this.contentContainer.innerHTML.substring(0, 200));

        // Verificar si hay elementos de tabla
        const tables = this.contentContainer.querySelectorAll('table');
        console.log('📊 Tablas encontradas:', tables.length);

        tables.forEach((table, index) => {
            console.log(`📊 Tabla ${index + 1}:`, table.className, table.rows.length, 'filas');
        });

        // Verificar si hay elementos de detalles_ventas
        const detallesVentas = this.contentContainer.querySelectorAll('[class*="detalles_ventas"]');
        console.log('🛒 Elementos de detalles_ventas encontrados:', detallesVentas.length);

        // Verificar si hay elementos de detalles_compras
        const detallesCompras = this.contentContainer.querySelectorAll('[class*="detalles_compras"]');
        console.log('🛍️ Elementos de detalles_compras encontrados:', detallesCompras.length);
    }

    loadDynamicModalsFromHTML(modalsHTML) {
    console.log('🔄 Cargando modales dinámicos desde HTML...');

    if (!modalsHTML || modalsHTML.trim() === '') {
        console.log('ℹ️ No hay HTML de modales para cargar');
        return;
    }

    // Parsear el HTML de modales
    const parser = new DOMParser();
    const modalsDoc = parser.parseFromString(modalsHTML, 'text/html');
    const modalsBlock = modalsDoc.querySelector('[data-modals]') || modalsDoc.body;

    if (!modalsBlock) {
        console.log('ℹ️ No se encontraron modales dinámicos en el HTML proporcionado');
        return;
    }

    // Contenedor de modales dinámicos
    const dynamicModalsContainer = document.getElementById('dynamic-modals');
    if (!dynamicModalsContainer) {
        console.warn('⚠️ Contenedor #dynamic-modals no encontrado');
        return;
    }

    // Limpiar modales previos
    dynamicModalsContainer.innerHTML = modalsBlock.innerHTML;
    console.log('✅ Modales dinámicos inyectados en el DOM');

    // Inicializar modales dinámicos de forma segura
    dynamicModalsContainer.querySelectorAll('.modal').forEach(modalEl => {
        bootstrap.Modal.getOrCreateInstance(modalEl);
    });

    // Función segura para mostrar modal
    function showModalById(modalId) {
        const modalEl = document.getElementById(modalId);
        if (!modalEl) return console.warn('⚠️ Modal no encontrado:', modalId);
        const instance = bootstrap.Modal.getOrCreateInstance(modalEl);
        instance.show();
    }

    // Reasignar triggers dinámicos manualmente
    dynamicModalsContainer.querySelectorAll('[data-bs-toggle="modal"]').forEach(trigger => {
        // Evitar duplicar listeners
        if (trigger._bsClickHandler) trigger.removeEventListener('click', trigger._bsClickHandler);

        const handler = e => {
            e.preventDefault();
            const targetId = trigger.dataset.bsTarget?.replace('#', '');
            if (targetId) showModalById(targetId);
        };

        trigger.addEventListener('click', handler);
        trigger._bsClickHandler = handler;
    });

    // Ejecutar scripts inline de los modales
    modalsBlock.querySelectorAll('script').forEach(script => {
        if (script.src) {
            const newScript = document.createElement('script');
            newScript.src = script.src;
            document.head.appendChild(newScript);
        } else if (script.textContent.trim()) {
            try { eval(script.textContent); } catch(e){ console.warn('Error script modal:', e); }
        }
    });

    // Reinicializar HTMX si existe
    if (typeof htmx !== 'undefined') htmx.process(dynamicModalsContainer);

    console.log('🔧 Modales dinámicos inicializados correctamente');
}




}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    window.ajaxNavigation = new AjaxNavigation();

    // Agregar función global para pruebas
    window.testAjaxNavigation = function(url) {
        console.log('🧪 Prueba manual de navegación AJAX a:', url);
        if (window.ajaxNavigation) {
            window.ajaxNavigation.navigateTo(url);
        } else {
            console.error('❌ AjaxNavigation no está inicializado');
        }
    };

    
});