python main.py4. Soporte para Fórmulas Matemáticas (Nemeth Braille): Una necesidad común en entornos académicos es la transcripción de matemáticas.
       * Sugerencia: Integrar una librería que convierta de LaTeX o MathML a código Nemeth Braille. Se podría añadir una acción
         "Insertar Fórmula Matemática" que abra un editor donde el usuario escriba la fórmula en LaTeX y esta se inserte en el texto
         como Braille especializado.

   7. Implementar un Entorno de Pruebas: Dada la complejidad de la aplicación, las pruebas automatizadas son cruciales para asegurar que
      los cambios no rompan funcionalidades existentes.
       * Sugerencia: Introducir la librería pytest junto con pytest-qt. Se puede empezar creando:
           * Tests Unitarios: Para la lógica pura en braille_processor.py y image_processor.py.
           * Tests de Integración: Para las funciones que ejecutan los workers en segundo plano.
           * Tests Funcionales: Para simular interacciones del usuario en la UI y verificar que el resultado es el esperado.



           Estudio de la función:
           Domini. Valor máximo y mínimo de X
           Imagen. Valor máximo y mínimo de Y
           Continuidad
           Corte eje Y
           Raices
          Intervalos: Creciente y decreciente
          Máximo relativo
            Mínimo relativo
          Máximo absoluto
          Mínimo relativo
          Puntos de inflexión
          Convexa
          Cóncava
          ¿Simérica?
          ¿Periódica?Vamos a añadir un nuevo botón en la 