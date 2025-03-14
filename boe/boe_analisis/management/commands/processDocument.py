__author__ = 'Carlos'
from django.db import models
from django.core.management.base import BaseCommand, CommandError
from boe_analisis.models import Diario, DocumentoAnuncio, Legislatura, Documento, Departamento, Rango, Origen_legislativo
from boe_analisis.models import Estado_consolidacion, Nota, Materia, Alerta, Palabra, Referencia
from boe_analisis.models import Modalidad, Tipo, Tramitacion, Procedimiento, Precio
import os
import sys
import locale
from django.db.models import Q
import re
from datetime import datetime
from lxml import etree, objectify
import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Obtener la última legislatura (con fin nulo)
last_legislatura = Legislatura.objects.filter(fin__isnull=True).first()
if last_legislatura:
    logging.info(f'Legislatura actual encontrada: {last_legislatura}')
else:
    logging.warning('No se encontró una legislatura activa')

class ProcessDocument():
    url_a_pattern = "http://www.boe.es/diario_boe/xml.php?id={0}"
    url_a_html_pattern = "http://www.boe.es/diario_boe/txt.php?id={0}"

    def __init__(self, url_xml):
        self.url = url_xml
        self.xmlDoc = None
        self.rootXML = None
        self.doc = Documento()
        self.metadatos = None
        self.analisis = None
        self.downloadXML()
        self.xmlToObject()
        self.getMetadatos()
        self.getAnalisis()
        self.createDocument()

    def downloadXML(self):
        """Descarga el contenido XML del BOE usando requests."""
        try:
            response = requests.get(self.url)
            response.raise_for_status()
            self.xmlDoc = response.content
        except requests.RequestException as e:
            logging.error(f"Error descargando XML desde {self.url}: {str(e)}")
            raise

    def xmlToObject(self):
        try:
            parser = etree.XMLParser(recover=True)
            self.rootXML = etree.fromstring(self.xmlDoc, parser=parser)
        except Exception as e:
            logging.error(f"Error parseando XML: {str(e)}")
            raise

    def getMetadatos(self):
        try:
            self.metadatos = self.rootXML.find(".//metadatos")
        except Exception as e:
            logging.error(f"Error obteniendo metadatos: {str(e)}")
            raise

    def getAnalisis(self):
        try:
            self.analisis = self.rootXML.find(".//analisis")
        except Exception as e:
            logging.error(f"Error obteniendo análisis: {str(e)}")
            raise

    def saveDoc(self):
        try:
            self.doc.save()
        except Exception as e:
            logging.error(f"Error guardando documento: {str(e)}")
            raise

    def isDocumentoAnuncio(self):
        seccion = self.getElement(self.metadatos, 'seccion')
        subseccion = self.getElement(self.metadatos, 'subseccion')
        return seccion == '5' and subseccion == 'A'

    def get_or_create(self, model, **kwargs):
        """
        Obtiene o crea un objeto del modelo especificado.
        Usa el método estándar de Django get_or_create.
        """
        busqueda = kwargs.get('busqueda', kwargs)
        insert = kwargs.get('insert', {})
        busqueda.update(insert)
        try:
            obj, created = model.objects.get_or_create(**busqueda)
            if created:
                logging.info(f'Creado nuevo objeto {model.__name__}: {obj}')
            return obj
        except Exception as e:
            logging.error(f'Error en get_or_create para {model.__name__}: {str(e)}')
            raise

    @staticmethod
    def stringToFloat(value):
        """Convierte una cadena con formato español a float."""
        try:
            return float(value.replace('.', '').replace(',', '.'))
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def textToDate(texto):
        """Convierte una cadena de fecha en formato YYYYMMDD a datetime."""
        if not texto:
            return None
        try:
            return datetime.strptime(texto, '%Y%m%d')
        except ValueError:
            return None

    @staticmethod
    def SiNoToBool(character):
        """Convierte 'S' o 'N' a booleano."""
        return True if character == 'S' else False if character == 'N' else None

    def existElement(self, origin, element):
        if origin is None:
            return False
        return hasattr(origin, element)

    def getElement(self, origin, element):
        if not self.existElement(origin, element):
            return None
        elem = getattr(origin, element)
        return elem.text if hasattr(elem, 'text') else elem

    def getElementCodigoTitulo(self, origin, element):
        if not self.existElement(origin, element):
            return None, None
        elem = getattr(origin, element)
        return elem.get('codigo'), elem.text if hasattr(elem, 'text') else None

    def getArrayOfElements(self, origin, element, subelement, model):
        if not self.existElement(origin, element):
            return []
        elements = getattr(origin, element)
        if not hasattr(elements, subelement):
            return []
        subelements = getattr(elements, subelement)
        if not isinstance(subelements, list):
            subelements = [subelements]
        result = []
        for sub in subelements:
            obj = self.get_or_create(model, texto=sub.text)
            result.append(obj)
        return result

    def processReferencias(self, doc):
        """Procesa las referencias anteriores y posteriores del documento."""
        if not self.existElement(self.analisis, 'referencias'):
            return

        ref = self.analisis.referencias

        # Procesar referencias anteriores
        if self.existElement(ref, 'anteriores') and self.existElement(ref.anteriores, 'anterior'):
            ref_ant = []
            for anterior in ref.anteriores.anterior:
                try:
                    referencia = anterior.get('referencia')
                    doc_ref = self.get_or_create(Documento, identificador=referencia)
                    palabra_codigo = anterior.palabra.get('codigo')
                    palabra_texto = anterior.palabra.text
                    texto = anterior.texto.text
                    palabra = self.get_or_create(Palabra, codigo=palabra_codigo, titulo=palabra_texto)
                    ref = self.get_or_create(Referencia, 
                                          busqueda={'referencia': doc_ref, 'palabra': palabra},
                                          insert={'texto': texto})
                    ref_ant.append(ref)
                except Exception as e:
                    logging.error(f"Error procesando referencia anterior {referencia}: {str(e)}")
            doc.referencias_anteriores = ref_ant

        # Procesar referencias posteriores
        if self.existElement(ref, 'posteriores') and self.existElement(ref.posteriores, 'posterior'):
            ref_post = []
            for posterior in ref.posteriores.posterior:
                try:
                    referencia = posterior.get('referencia')
                    doc_ref = self.get_or_create(Documento, identificador=referencia)
                    palabra_codigo = posterior.palabra.get('codigo')
                    palabra_texto = posterior.palabra.text
                    texto = posterior.texto.text
                    palabra = self.get_or_create(Palabra, codigo=palabra_codigo, titulo=palabra_texto)
                    ref = self.get_or_create(Referencia,
                                          busqueda={'referencia': doc_ref, 'palabra': palabra},
                                          insert={'texto': texto})
                    ref_post.append(ref)
                except Exception as e:
                    logging.error(f"Error procesando referencia posterior {referencia}: {str(e)}")
            doc.referencias_posteriores = ref_post

    def createDocument(self):
        """Crea o actualiza un documento con todos sus metadatos y relaciones."""
        try:
            # Obtener identificador
            identificador = self.getElement(self.metadatos, 'identificador')
            if not identificador:
                raise ValueError("Identificador no encontrado")

            # Determinar tipo de documento y procesarlo
            if self.isDocumentoAnuncio():
                self.doc = self.get_or_create(DocumentoAnuncio, identificador=identificador)
                self._process_anuncio()
            else:
                self.doc = self.get_or_create(Documento, identificador=identificador)

            # Procesar metadatos comunes
            self._process_common_metadata()

            # Procesar fechas
            self._process_dates()

            # Procesar URLs
            self._process_urls()

            # Procesar relaciones
            self._process_relationships()

            # Procesar texto
            self.doc.texto = etree.tostring(self.rootXML.texto, pretty_print=True, encoding='unicode')

        except Exception as e:
            logging.error(f"Error creando documento {identificador if identificador else 'desconocido'}: {str(e)}")
            raise

    def _process_anuncio(self):
        """Procesa los campos específicos de un documento anuncio."""
        # Modalidad
        mod_codigo, mod_titulo = self.getElementCodigoTitulo(self.analisis, 'modalidad')
        self.doc.modalidad = self.get_or_create(Modalidad, codigo=mod_codigo, titulo=mod_titulo)

        # Tipo
        tipo_codigo, tipo_titulo = self.getElementCodigoTitulo(self.analisis, 'tipo')
        self.doc.tipo = self.get_or_create(Tipo, codigo=tipo_codigo, titulo=tipo_titulo)

        # Tramitación
        tram_codigo, tram_titulo = self.getElementCodigoTitulo(self.analisis, 'tramitacion')
        self.doc.tramitacion = self.get_or_create(Tramitacion, codigo=tram_codigo, titulo=tram_titulo)

        # Procedimiento
        proc_codigo, proc_titulo = self.getElementCodigoTitulo(self.analisis, 'procedimiento')
        self.doc.procedimiento = self.get_or_create(Procedimiento, codigo=proc_codigo, titulo=proc_titulo)

        # Fechas específicas
        self.doc.fecha_presentacion_ofertas = self.getElement(self.analisis, 'fecha_presentacion_ofertas')
        self.doc.fecha_apertura_ofertas = self.getElement(self.analisis, 'fecha_apertura_ofertas')

        # Precio e importe
        precio_codigo, precio_titulo = self.getElementCodigoTitulo(self.analisis, 'precio')
        self.doc.precio = self.get_or_create(Precio, codigo=precio_codigo, titulo=precio_titulo)
        
        importe = self.getElement(self.analisis, 'importe')
        if isinstance(importe, str):
            self.doc.importe = self.stringToFloat(importe)

        # Otros campos
        self.doc.ambito_geografico = self.getElement(self.analisis, 'ambito_geografico')
        self.doc.materias_anuncio = self.getElement(self.analisis, 'materias')
        self.doc.materias_cpv = self.getElement(self.analisis, 'materias_cpv')
        self.doc.observaciones = self.getElement(self.analisis, 'observaciones')

    def _process_common_metadata(self):
        """Procesa los metadatos comunes a todos los documentos."""
        doc = self.doc
        doc.seccion = self.getElement(self.metadatos, 'seccion')
        doc.subseccion = self.getElement(self.metadatos, 'subseccion')
        doc.titulo = self.getElement(self.metadatos, 'titulo')

        # Diario
        diario_codigo, diario_titulo = self.getElementCodigoTitulo(self.metadatos, 'diario')
        doc.diario = self.get_or_create(Diario, codigo=diario_codigo, titulo=diario_titulo)
        doc.diario_numero = self.getElement(self.metadatos, 'diario_numero')

        # Departamento
        dep_codigo, dep_titulo = self.getElementCodigoTitulo(self.metadatos, 'departamento')
        doc.departamento = self.get_or_create(Departamento, codigo=dep_codigo, titulo=dep_titulo)

        # Rango
        rango_codigo, rango_titulo = self.getElementCodigoTitulo(self.metadatos, 'rango')
        doc.rango = self.get_or_create(Rango, codigo=rango_codigo, titulo=rango_titulo)

        doc.numero_oficial = self.getElement(self.metadatos, 'numero_oficial')

    def _process_dates(self):
        """Procesa todas las fechas del documento."""
        doc = self.doc
        
        # Fecha disposición y legislatura
        doc.fecha_disposicion = self.textToDate(self.getElement(self.metadatos, 'fecha_disposicion'))
        if doc.fecha_disposicion:
            if last_legislatura and doc.fecha_disposicion.date() >= last_legislatura.inicio:
                doc.legislatura = last_legislatura
                logging.info(f'Asignada legislatura actual: {last_legislatura}')
            else:
                legislatura = Legislatura.objects.filter(
                    inicio__lte=doc.fecha_disposicion,
                    fin__gte=doc.fecha_disposicion
                ).first()
                if legislatura:
                    logging.info(f'Asignada legislatura histórica: {legislatura}')
                    doc.legislatura = legislatura
                else:
                    logging.warning(f'No se encontró legislatura para la fecha {doc.fecha_disposicion}')

        # Otras fechas
        doc.fecha_publicacion = self.textToDate(self.getElement(self.metadatos, 'fecha_publicacion'))
        doc.fecha_vigencia = self.textToDate(self.getElement(self.metadatos, 'fecha_vigencia'))
        doc.fecha_derogacion = self.textToDate(self.getElement(self.metadatos, 'fecha_derogacion'))

    def _process_urls(self):
        """Procesa todas las URLs del documento."""
        doc = self.doc
        doc.url_htm = self.url_a_html_pattern.format(doc.identificador)
        doc.url_xml = self.url_a_pattern.format(doc.identificador)
        doc.url_epub = self.getElement(self.metadatos, 'url_epub')
        doc.url_pdf = self.getElement(self.metadatos, 'url_pdf')
        doc.url_pdf_catalan = self.getElement(self.metadatos, 'url_pdf_catalan')
        doc.url_pdf_euskera = self.getElement(self.metadatos, 'url_pdf_euskera')
        doc.url_pdf_gallego = self.getElement(self.metadatos, 'url_pdf_gallego')
        doc.url_pdf_valenciano = self.getElement(self.metadatos, 'url_pdf_valenciano')

    def _process_relationships(self):
        """Procesa todas las relaciones del documento."""
        doc = self.doc
        
        # Estado de consolidación
        est_cons_cod, est_cons_titulo = self.getElementCodigoTitulo(self.metadatos, 'estado_consolidacion')
        if est_cons_cod and est_cons_cod.strip():
            doc.estado_consolidacion = self.get_or_create(
                Estado_consolidacion,
                codigo=int(est_cons_cod),
                titulo=est_cons_titulo
            )

        # Origen legislativo
        origen_leg_cod, origen_leg_titulo = self.getElementCodigoTitulo(self.metadatos, 'origen_legislativo')
        doc.origen_legislativo = self.get_or_create(
            Origen_legislativo,
            codigo=origen_leg_cod,
            titulo=origen_leg_titulo
        )

        # Campos booleanos
        doc.judicialmente_anulada = self.SiNoToBool(self.getElement(self.metadatos, 'judicialmente_anulada'))
        doc.vigencia_agotada = self.SiNoToBool(self.getElement(self.metadatos, 'vigencia_agotada'))
        doc.estatus_derogacion = self.SiNoToBool(self.getElement(self.metadatos, 'estatus_derogacion'))

        # Relaciones M2M
        doc.notas = self.getArrayOfElements(self.analisis, 'notas', 'nota', Nota)
        doc.materias = self.getArrayOfElements(self.analisis, 'materias', 'materia', Materia)
        doc.alertas = self.getArrayOfElements(self.analisis, 'alertas', 'alerta', Alerta)

        # Referencias
        self.processReferencias(doc)