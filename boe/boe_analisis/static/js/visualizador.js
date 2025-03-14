/**
 * Visualizador de documentos del BOE
 * Script para manejar la visualización y análisis de documentos del BOE
 */

document.addEventListener('DOMContentLoaded', function() {
    inicializarVisualizador();
    inicializarResaltado();
    inicializarAcciones();
    inicializarCompartir();
});

/**
 * Inicializa el visualizador de documentos
 */
function inicializarVisualizador() {
    // Manejar cambio de pestañas
    const tabsDocumento = document.querySelectorAll('.nav-link[data-bs-toggle="tab"]');
    if (tabsDocumento.length > 0) {
        tabsDocumento.forEach(tab => {
            tab.addEventListener('shown.bs.tab', function(e) {
                // Guardar la pestaña activa en localStorage
                localStorage.setItem('ultimaPestanaDocumento', e.target.getAttribute('href'));
            });
        });
        
        // Restaurar la última pestaña activa
        const ultimaPestana = localStorage.getItem('ultimaPestanaDocumento');
        if (ultimaPestana) {
            const tab = document.querySelector(`.nav-link[href="${ultimaPestana}"]`);
            if (tab) {
                new bootstrap.Tab(tab).show();
            }
        }
    }
    
    // Inicializar el zoom del texto
    const btnAumentarTexto = document.getElementById('aumentar-texto');
    const btnDisminuirTexto = document.getElementById('disminuir-texto');
    const btnResetearTexto = document.getElementById('resetear-texto');
    
    if (btnAumentarTexto && btnDisminuirTexto && btnResetearTexto) {
        const contenidoDocumento = document.querySelector('.contenido-documento');
        let tamanoActual = 100;
        
        btnAumentarTexto.addEventListener('click', function() {
            tamanoActual += 10;
            aplicarZoom(contenidoDocumento, tamanoActual);
        });
        
        btnDisminuirTexto.addEventListener('click', function() {
            tamanoActual -= 10;
            if (tamanoActual < 50) tamanoActual = 50;
            aplicarZoom(contenidoDocumento, tamanoActual);
        });
        
        btnResetearTexto.addEventListener('click', function() {
            tamanoActual = 100;
            aplicarZoom(contenidoDocumento, tamanoActual);
        });
    }
}

/**
 * Aplica zoom al contenido del documento
 * @param {HTMLElement} elemento - Elemento al que aplicar zoom
 * @param {number} porcentaje - Porcentaje de zoom
 */
function aplicarZoom(elemento, porcentaje) {
    if (!elemento) return;
    elemento.style.fontSize = `${porcentaje}%`;
    
    // Guardar preferencia del usuario
    localStorage.setItem('zoomDocumento', porcentaje);
    
    // Actualizar indicador
    const indicadorZoom = document.getElementById('zoom-actual');
    if (indicadorZoom) {
        indicadorZoom.textContent = `${porcentaje}%`;
    }
}

/**
 * Inicializa el resaltado de términos en el documento
 */
function inicializarResaltado() {
    const inputBuscar = document.getElementById('buscar-en-documento');
    const btnBuscar = document.getElementById('btn-buscar-documento');
    
    if (inputBuscar && btnBuscar) {
        btnBuscar.addEventListener('click', function() {
            buscarEnDocumento(inputBuscar.value);
        });
        
        inputBuscar.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                buscarEnDocumento(inputBuscar.value);
            }
        });
    }
    
    // Resaltar palabras clave de la alerta automáticamente
    const contenidoDocumento = document.querySelector('.contenido-documento');
    const palabrasClave = document.getElementById('palabras-clave-alerta');
    
    if (contenidoDocumento && palabrasClave && palabrasClave.dataset.palabras) {
        const palabras = JSON.parse(palabrasClave.dataset.palabras);
        if (palabras && palabras.length > 0) {
            resaltarPalabras(contenidoDocumento, palabras);
        }
    }
}

/**
 * Busca y resalta términos en el documento
 * @param {string} termino - Término a buscar
 */
function buscarEnDocumento(termino) {
    if (!termino) return;
    
    const contenidoDocumento = document.querySelector('.contenido-documento');
    if (!contenidoDocumento) return;
    
    // Eliminar resaltados anteriores de búsqueda
    const resaltadosAnteriores = contenidoDocumento.querySelectorAll('.resaltado-busqueda');
    resaltadosAnteriores.forEach(el => {
        const padre = el.parentNode;
        padre.replaceChild(document.createTextNode(el.textContent), el);
    });
    
    // Normalizar el contenido después de eliminar los resaltados
    contenidoDocumento.normalize();
    
    // Resaltar el nuevo término
    const terminos = termino.split(' ').filter(t => t.trim() !== '');
    if (terminos.length > 0) {
        resaltarPalabras(contenidoDocumento, terminos, 'resaltado-busqueda');
        
        // Desplazarse al primer resultado
        const primerResultado = contenidoDocumento.querySelector('.resaltado-busqueda');
        if (primerResultado) {
            primerResultado.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        
        // Mostrar contador de resultados
        const resultados = contenidoDocumento.querySelectorAll('.resaltado-busqueda');
        mostrarContadorResultados(resultados.length);
    }
}

/**
 * Resalta palabras específicas en un elemento
 * @param {HTMLElement} elemento - Elemento donde buscar
 * @param {Array} palabras - Array de palabras a resaltar
 * @param {string} clase - Clase CSS para el resaltado
 */
function resaltarPalabras(elemento, palabras, clase = 'resaltado-alerta') {
    if (!elemento || !palabras || palabras.length === 0) return;
    
    // Crear expresión regular para buscar todas las palabras
    const regex = new RegExp(palabras.map(p => escapeRegExp(p)).join('|'), 'gi');
    
    // Función recursiva para recorrer todos los nodos de texto
    function recorrerNodos(nodo) {
        if (nodo.nodeType === Node.TEXT_NODE) {
            const texto = nodo.nodeValue;
            if (regex.test(texto)) {
                // Crear un elemento temporal
                const span = document.createElement('span');
                
                // Reemplazar todas las coincidencias con spans resaltados
                span.innerHTML = texto.replace(regex, match => `<span class="${clase}">${match}</span>`);
                
                // Reemplazar el nodo de texto con el span
                const padre = nodo.parentNode;
                padre.replaceChild(span, nodo);
            }
        } else if (nodo.nodeType === Node.ELEMENT_NODE && nodo.nodeName !== 'SCRIPT' && nodo.nodeName !== 'STYLE') {
            // Recorrer hijos si es un elemento (excepto scripts y estilos)
            Array.from(nodo.childNodes).forEach(recorrerNodos);
        }
    }
    
    // Iniciar recorrido desde el elemento raíz
    recorrerNodos(elemento);
}

/**
 * Escapa caracteres especiales para usar en expresiones regulares
 * @param {string} texto - Texto a escapar
 * @return {string} Texto escapado
 */
function escapeRegExp(texto) {
    return texto.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Muestra el contador de resultados de búsqueda
 * @param {number} cantidad - Cantidad de resultados
 */
function mostrarContadorResultados(cantidad) {
    const contador = document.getElementById('contador-resultados');
    if (contador) {
        contador.textContent = cantidad;
        contador.parentElement.classList.remove('d-none');
    }
}

/**
 * Inicializa las acciones para el documento
 */
function inicializarAcciones() {
    // Botón para guardar documento
    const btnGuardar = document.getElementById('guardar-documento');
    if (btnGuardar) {
        btnGuardar.addEventListener('click', function() {
            const documentoId = this.dataset.documentoId;
            guardarDocumento(documentoId);
        });
    }
    
    // Botón para imprimir documento
    const btnImprimir = document.getElementById('imprimir-documento');
    if (btnImprimir) {
        btnImprimir.addEventListener('click', function() {
            imprimirDocumento();
        });
    }
    
    // Botón para exportar a PDF
    const btnExportarPDF = document.getElementById('exportar-pdf');
    if (btnExportarPDF) {
        btnExportarPDF.addEventListener('click', function() {
            const documentoId = this.dataset.documentoId;
            exportarPDF(documentoId);
        });
    }
}

/**
 * Guarda un documento en la biblioteca del usuario
 * @param {string} documentoId - ID del documento
 */
function guardarDocumento(documentoId) {
    fetch('/documentos/guardar/' + documentoId + '/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            mostrarToast('Documento guardado', 'El documento ha sido guardado en tu biblioteca.', 'success');
            
            // Actualizar botón
            const btnGuardar = document.getElementById('guardar-documento');
            if (btnGuardar) {
                btnGuardar.innerHTML = '<i class="fas fa-check me-1"></i>Guardado';
                btnGuardar.classList.remove('btn-outline-primary');
                btnGuardar.classList.add('btn-success');
                btnGuardar.disabled = true;
            }
        } else {
            mostrarToast('Error', data.error || 'Ha ocurrido un error al guardar el documento.', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        mostrarToast('Error', 'Ha ocurrido un error al guardar el documento.', 'danger');
    });
}

/**
 * Imprime el documento actual
 */
function imprimirDocumento() {
    // Crear una ventana de impresión con solo el contenido del documento
    const contenido = document.querySelector('.contenido-documento').innerHTML;
    const titulo = document.querySelector('h1').textContent;
    
    const ventanaImpresion = window.open('', '_blank');
    ventanaImpresion.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>${titulo}</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }
                h1 { font-size: 24px; margin-bottom: 20px; }
                .fecha { color: #666; margin-bottom: 30px; }
                .contenido { margin-top: 20px; }
                .resaltado-alerta { background-color: #ffeb3b; padding: 2px; }
                @media print {
                    body { font-size: 12pt; }
                    h1 { font-size: 18pt; }
                }
            </style>
        </head>
        <body>
            <h1>${titulo}</h1>
            <div class="contenido">${contenido}</div>
            <script>
                window.onload = function() { window.print(); window.close(); }
            </script>
        </body>
        </html>
    `);
    ventanaImpresion.document.close();
}

/**
 * Exporta el documento a PDF
 * @param {string} documentoId - ID del documento
 */
function exportarPDF(documentoId) {
    // Mostrar indicador de carga
    const btnExportar = document.getElementById('exportar-pdf');
    const textoOriginal = btnExportar.innerHTML;
    btnExportar.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>Generando PDF...';
    btnExportar.disabled = true;
    
    // Solicitar generación de PDF
    fetch('/documentos/exportar-pdf/' + documentoId + '/', {
        method: 'GET',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Error al generar el PDF');
        }
        return response.blob();
    })
    .then(blob => {
        // Crear URL para el blob
        const url = window.URL.createObjectURL(blob);
        
        // Crear un enlace para descargar el archivo
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = 'documento_boe_' + documentoId + '.pdf';
        
        // Añadir al DOM y hacer clic
        document.body.appendChild(a);
        a.click();
        
        // Limpiar
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        // Restaurar botón
        btnExportar.innerHTML = textoOriginal;
        btnExportar.disabled = false;
    })
    .catch(error => {
        console.error('Error:', error);
        mostrarToast('Error', 'Ha ocurrido un error al generar el PDF.', 'danger');
        
        // Restaurar botón
        btnExportar.innerHTML = textoOriginal;
        btnExportar.disabled = false;
    });
}

/**
 * Inicializa las funciones para compartir documentos
 */
function inicializarCompartir() {
    // Compartir en redes sociales
    document.querySelectorAll('.compartir-social').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            
            const red = this.dataset.red;
            const url = window.location.href;
            const titulo = document.querySelector('h1').textContent;
            
            let urlCompartir = '';
            
            switch (red) {
                case 'twitter':
                    urlCompartir = `https://twitter.com/intent/tweet?text=${encodeURIComponent(titulo)}&url=${encodeURIComponent(url)}`;
                    break;
                case 'facebook':
                    urlCompartir = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`;
                    break;
                case 'linkedin':
                    urlCompartir = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`;
                    break;
                case 'email':
                    urlCompartir = `mailto:?subject=${encodeURIComponent('Documento BOE: ' + titulo)}&body=${encodeURIComponent('He encontrado este documento que puede interesarte: ' + url)}`;
                    break;
            }
            
            if (urlCompartir) {
                window.open(urlCompartir, '_blank', 'width=600,height=400');
            }
        });
    });
    
    // Copiar enlace
    const btnCopiarEnlace = document.getElementById('copiar-enlace');
    if (btnCopiarEnlace) {
        btnCopiarEnlace.addEventListener('click', function() {
            const url = window.location.href;
            
            // Copiar al portapapeles
            navigator.clipboard.writeText(url)
                .then(() => {
                    // Cambiar texto del botón temporalmente
                    const textoOriginal = this.innerHTML;
                    this.innerHTML = '<i class="fas fa-check me-1"></i>Copiado';
                    
                    setTimeout(() => {
                        this.innerHTML = textoOriginal;
                    }, 2000);
                    
                    mostrarToast('Enlace copiado', 'El enlace ha sido copiado al portapapeles.', 'success');
                })
                .catch(err => {
                    console.error('Error al copiar:', err);
                    mostrarToast('Error', 'No se pudo copiar el enlace.', 'danger');
                });
        });
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
