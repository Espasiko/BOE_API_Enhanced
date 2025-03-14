/**
 * BOE Alertas - Script principal para el sistema de alertas
 */

document.addEventListener('DOMContentLoaded', function() {
    // Inicializar componentes
    inicializarSelect2();
    inicializarTagsInput();
    inicializarTooltips();
    inicializarToggleAlertas();
    inicializarNotificaciones();
    inicializarGraficos();
    
    // Manejar formularios
    configurarFormularioAlertas();
});

/**
 * Inicializa el componente Select2 para selecciones múltiples
 */
function inicializarSelect2() {
    if (typeof $.fn.select2 !== 'undefined') {
        $('.select2').select2({
            theme: 'bootstrap4',
            placeholder: 'Seleccionar opciones',
            allowClear: true,
            width: '100%'
        });
    }
}

/**
 * Inicializa el componente Bootstrap Tags Input para palabras clave
 */
function inicializarTagsInput() {
    if (typeof $.fn.tagsinput !== 'undefined') {
        $('.tags-input').tagsinput({
            trimValue: true,
            confirmKeys: [13, 44, 32], // Enter, coma, espacio
            tagClass: function() {
                return 'badge badge-primary';
            }
        });
    }
}

/**
 * Inicializa los tooltips de Bootstrap
 */
function inicializarTooltips() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Inicializa los interruptores para activar/desactivar alertas
 */
function inicializarToggleAlertas() {
    document.querySelectorAll('.toggle-alerta').forEach(function(toggle) {
        toggle.addEventListener('change', function() {
            const alertaId = this.dataset.alertaId;
            const estado = this.checked;
            
            // Mostrar spinner mientras se procesa
            const card = this.closest('.card-alerta');
            card.classList.add('processing');
            
            // Enviar solicitud AJAX para cambiar el estado
            fetch('/alertas/toggle/' + alertaId + '/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ activa: estado })
            })
            .then(response => response.json())
            .then(data => {
                card.classList.remove('processing');
                
                if (data.success) {
                    // Actualizar la UI
                    if (estado) {
                        card.classList.remove('inactiva');
                        card.classList.add('activa');
                        mostrarToast('Alerta activada', 'La alerta ha sido activada correctamente.', 'success');
                    } else {
                        card.classList.remove('activa');
                        card.classList.add('inactiva');
                        mostrarToast('Alerta desactivada', 'La alerta ha sido desactivada correctamente.', 'warning');
                    }
                } else {
                    // Revertir el cambio en caso de error
                    this.checked = !estado;
                    mostrarToast('Error', data.error || 'Ha ocurrido un error al cambiar el estado de la alerta.', 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                card.classList.remove('processing');
                this.checked = !estado;
                mostrarToast('Error', 'Ha ocurrido un error al cambiar el estado de la alerta.', 'danger');
            });
        });
    });
}

/**
 * Inicializa las funciones para manejar notificaciones
 */
function inicializarNotificaciones() {
    // Marcar notificación como leída
    document.querySelectorAll('.marcar-leida').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const notificacionId = this.dataset.notificacionId;
            cambiarEstadoNotificacion(notificacionId, 'leida', this);
        });
    });
    
    // Marcar notificación como archivada
    document.querySelectorAll('.marcar-archivada').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const notificacionId = this.dataset.notificacionId;
            cambiarEstadoNotificacion(notificacionId, 'archivada', this);
        });
    });
    
    // Marcar todas las notificaciones como leídas
    const btnMarcarTodasLeidas = document.getElementById('marcar-todas-leidas');
    if (btnMarcarTodasLeidas) {
        btnMarcarTodasLeidas.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Mostrar confirmación
            if (!confirm('¿Estás seguro de que deseas marcar todas las notificaciones como leídas?')) {
                return;
            }
            
            // Enviar solicitud AJAX
            fetch('/notificaciones/marcar-todas-leidas/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Actualizar la UI
                    document.querySelectorAll('.notificacion-card.pendiente').forEach(function(card) {
                        card.classList.remove('pendiente');
                        card.classList.add('leida');
                    });
                    
                    // Actualizar contadores
                    actualizarContadorNotificaciones(0);
                    
                    mostrarToast('Notificaciones actualizadas', 'Todas las notificaciones han sido marcadas como leídas.', 'success');
                } else {
                    mostrarToast('Error', data.error || 'Ha ocurrido un error al actualizar las notificaciones.', 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                mostrarToast('Error', 'Ha ocurrido un error al actualizar las notificaciones.', 'danger');
            });
        });
    }
}

/**
 * Cambia el estado de una notificación
 * @param {number} notificacionId - ID de la notificación
 * @param {string} estado - Nuevo estado ('leida' o 'archivada')
 * @param {HTMLElement} btnElement - Elemento del botón que se hizo clic
 */
function cambiarEstadoNotificacion(notificacionId, estado, btnElement) {
    // Obtener el elemento de la tarjeta
    const card = btnElement.closest('.notificacion-card');
    card.classList.add('processing');
    
    // Enviar solicitud AJAX
    fetch('/notificaciones/cambiar-estado/' + notificacionId + '/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ estado: estado })
    })
    .then(response => response.json())
    .then(data => {
        card.classList.remove('processing');
        
        if (data.success) {
            // Actualizar la UI
            card.classList.remove('pendiente', 'leida', 'archivada');
            card.classList.add(estado);
            
            // Actualizar contadores
            if (data.pendientes !== undefined) {
                actualizarContadorNotificaciones(data.pendientes);
            }
            
            // Mensaje de éxito
            let mensaje = '';
            if (estado === 'leida') {
                mensaje = 'La notificación ha sido marcada como leída.';
            } else if (estado === 'archivada') {
                mensaje = 'La notificación ha sido archivada.';
            }
            
            mostrarToast('Notificación actualizada', mensaje, 'success');
            
            // Si estamos en la página de lista y hay filtros, ocultar la tarjeta
            const filtroActual = new URLSearchParams(window.location.search).get('estado');
            if (filtroActual && filtroActual !== estado) {
                card.style.display = 'none';
            }
        } else {
            mostrarToast('Error', data.error || 'Ha ocurrido un error al cambiar el estado de la notificación.', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        card.classList.remove('processing');
        mostrarToast('Error', 'Ha ocurrido un error al cambiar el estado de la notificación.', 'danger');
    });
}

/**
 * Actualiza el contador de notificaciones pendientes
 * @param {number} cantidad - Nueva cantidad de notificaciones pendientes
 */
function actualizarContadorNotificaciones(cantidad) {
    // Actualizar el contador en el menú
    const contadorMenu = document.getElementById('contador-notificaciones');
    if (contadorMenu) {
        contadorMenu.textContent = cantidad;
        contadorMenu.style.display = cantidad > 0 ? 'inline-block' : 'none';
    }
    
    // Actualizar el contador en la página de notificaciones
    const contadorPagina = document.getElementById('total-pendientes');
    if (contadorPagina) {
        contadorPagina.textContent = cantidad;
    }
}

/**
 * Configura los formularios de alertas
 */
function configurarFormularioAlertas() {
    // Validación de formulario
    const formularioAlerta = document.getElementById('formulario-alerta');
    if (formularioAlerta) {
        formularioAlerta.addEventListener('submit', function(e) {
            if (!this.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            
            this.classList.add('was-validated');
        });
    }
    
    // Previsualización de palabras clave
    const inputPalabrasClave = document.getElementById('id_palabras_clave');
    const previewPalabrasClave = document.getElementById('preview-palabras-clave');
    
    if (inputPalabrasClave && previewPalabrasClave) {
        inputPalabrasClave.addEventListener('change', function() {
            actualizarPreviewPalabrasClave(this.value, previewPalabrasClave);
        });
        
        // Inicializar con el valor actual
        actualizarPreviewPalabrasClave(inputPalabrasClave.value, previewPalabrasClave);
    }
}

/**
 * Actualiza la previsualización de palabras clave
 * @param {string} palabrasClave - Lista de palabras clave separadas por comas
 * @param {HTMLElement} container - Contenedor para la previsualización
 */
function actualizarPreviewPalabrasClave(palabrasClave, container) {
    container.innerHTML = '';
    
    if (!palabrasClave) {
        container.innerHTML = '<p class="text-muted">No hay palabras clave definidas</p>';
        return;
    }
    
    const palabras = palabrasClave.split(',');
    palabras.forEach(function(palabra) {
        palabra = palabra.trim();
        if (palabra) {
            const span = document.createElement('span');
            span.className = 'alerta-keyword';
            span.textContent = palabra;
            container.appendChild(span);
        }
    });
}

/**
 * Inicializa los gráficos en la página de estadísticas
 */
function inicializarGraficos() {
    // Gráfico de estados de notificaciones
    const ctxEstados = document.getElementById('grafico-estados');
    if (ctxEstados) {
        const labels = JSON.parse(ctxEstados.dataset.labels);
        const data = JSON.parse(ctxEstados.dataset.values);
        const colors = JSON.parse(ctxEstados.dataset.colors);
        
        new Chart(ctxEstados, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: colors,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }
    
    // Gráfico de notificaciones por alerta
    const ctxAlertas = document.getElementById('grafico-alertas');
    if (ctxAlertas) {
        const labels = JSON.parse(ctxAlertas.dataset.labels);
        const data = JSON.parse(ctxAlertas.dataset.values);
        const colors = JSON.parse(ctxAlertas.dataset.colors);
        
        new Chart(ctxAlertas, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Notificaciones',
                    data: data,
                    backgroundColor: colors,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }
    
    // Gráfico de relevancia
    const ctxRelevancia = document.getElementById('grafico-relevancia');
    if (ctxRelevancia) {
        const labels = JSON.parse(ctxRelevancia.dataset.labels);
        const data = JSON.parse(ctxRelevancia.dataset.values);
        const colors = JSON.parse(ctxRelevancia.dataset.colors);
        
        new Chart(ctxRelevancia, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: colors,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }
    
    // Gráfico de tendencia
    const ctxTendencia = document.getElementById('grafico-tendencia');
    if (ctxTendencia) {
        const labels = JSON.parse(ctxTendencia.dataset.labels);
        const data = JSON.parse(ctxTendencia.dataset.values);
        
        new Chart(ctxTendencia, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Notificaciones',
                    data: data,
                    borderColor: '#2196F3',
                    backgroundColor: 'rgba(33, 150, 243, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        }
                    }
                }
            }
        });
    }
    
    // Nube de palabras clave
    const palabrasContainer = document.getElementById('nube-palabras');
    if (palabrasContainer) {
        const labels = JSON.parse(palabrasContainer.dataset.labels);
        const data = JSON.parse(palabrasContainer.dataset.values);
        
        if (typeof d3 !== 'undefined' && typeof d3.layout.cloud !== 'undefined') {
            const width = palabrasContainer.offsetWidth;
            const height = 300;
            
            // Crear datos para la nube de palabras
            const palabras = labels.map((palabra, i) => ({
                text: palabra,
                size: 10 + (data[i] * 5) // Tamaño basado en la frecuencia
            }));
            
            // Crear la nube de palabras
            d3.layout.cloud()
                .size([width, height])
                .words(palabras)
                .padding(5)
                .rotate(() => ~~(Math.random() * 2) * 90)
                .font("Arial")
                .fontSize(d => d.size)
                .on("end", dibujarNubePalabras)
                .start();
                
            function dibujarNubePalabras(words) {
                d3.select(palabrasContainer).append("svg")
                    .attr("width", width)
                    .attr("height", height)
                    .append("g")
                    .attr("transform", `translate(${width/2},${height/2})`)
                    .selectAll("text")
                    .data(words)
                    .enter().append("text")
                    .style("font-size", d => `${d.size}px`)
                    .style("font-family", "Arial")
                    .style("fill", () => d3.interpolateInferno(Math.random()))
                    .attr("text-anchor", "middle")
                    .attr("transform", d => `translate(${d.x},${d.y})rotate(${d.rotate})`)
                    .text(d => d.text);
            }
        }
    }
}

/**
 * Muestra un mensaje toast
 * @param {string} titulo - Título del mensaje
 * @param {string} mensaje - Contenido del mensaje
 * @param {string} tipo - Tipo de mensaje (success, warning, danger, info)
 */
function mostrarToast(titulo, mensaje, tipo) {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) return;
    
    const toastId = 'toast-' + Date.now();
    const html = `
        <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header bg-${tipo} text-white">
                <strong class="me-auto">${titulo}</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Cerrar"></button>
            </div>
            <div class="toast-body">
                ${mensaje}
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', html);
    
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { autohide: true, delay: 5000 });
    toast.show();
    
    // Eliminar el toast del DOM después de ocultarse
    toastElement.addEventListener('hidden.bs.toast', function() {
        this.remove();
    });
}

/**
 * Obtiene el valor de una cookie
 * @param {string} name - Nombre de la cookie
 * @return {string} Valor de la cookie
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
