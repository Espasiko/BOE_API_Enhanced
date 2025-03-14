"""
Adaptador para Pattern que permite usar alternativas cuando Pattern no está disponible.
Este archivo facilita la compatibilidad entre entornos con diferentes versiones de Python.
"""

try:
    # Intenta importar Pattern (entorno local)
    from pattern.es import parse, conjugate, INFINITIVE, PRESENT, PAST, FUTURE
    from pattern.es import singularize, pluralize, comparative, superlative
    from pattern.es import predicative, attributive
    PATTERN_AVAILABLE = True
    print("Usando Pattern original")
except ImportError:
    # Usa textblob como alternativa (PythonAnywhere)
    from textblob import TextBlob
    PATTERN_AVAILABLE = False
    print("Usando adaptador TextBlob para Pattern")
    
    # Constantes de Pattern
    INFINITIVE = 1
    PRESENT = 2
    PAST = 3
    FUTURE = 4
    
    def parse(text, *args, **kwargs):
        """Implementación alternativa usando textblob"""
        blob = TextBlob(text)
        return " ".join([word for word in blob.words])
    
    def conjugate(verb, tense=INFINITIVE, *args, **kwargs):
        """Implementación simplificada de conjugación"""
        # Simplemente devuelve el verbo sin conjugar
        return verb
    
    def singularize(word):
        """Convierte una palabra a singular"""
        blob = TextBlob(word)
        return blob.words[0].singularize()
    
    def pluralize(word):
        """Convierte una palabra a plural"""
        blob = TextBlob(word)
        return blob.words[0].pluralize()
    
    def comparative(word):
        """Forma comparativa (no implementada completamente)"""
        return "más " + word
    
    def superlative(word):
        """Forma superlativa (no implementada completamente)"""
        return "el más " + word
    
    def predicative(word):
        """Forma predicativa (simplemente devuelve la palabra)"""
        return word
    
    def attributive(word):
        """Forma atributiva (simplemente devuelve la palabra)"""
        return word
