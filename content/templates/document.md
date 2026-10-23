---
# ── Frontmatter ─────────────────────────────────────────────────────────────
# Obligatorios: type y title. Todo lo demás es opcional.
type: document            # document o deck
title: Plantilla de documento
subtitle: Todos los bloques disponibles, con su sintaxis
author: S4nti4goCoder
date: 2026-10-22          # se muestra tal cual
cover: true               # portada a página completa (por defecto: false)
toc: true                 # índice con números de página (por defecto: false)
tocDepth: 2               # niveles de título que entran al índice (por defecto: 2)
# maxPages: 10            # opcional: aviso y código de salida 1 si se pasa
# lang: es                # idioma del documento, para el guionado (por defecto: es)
---
# Títulos y texto

Cada título de nivel 1 (`# Título`) es un capítulo: empieza en una página nueva, entra
al índice y aparece arriba a la derecha en el encabezado de sus páginas.

## Títulos de nivel 2

Los títulos de nivel 2, 3 y 4 nunca quedan huérfanos al final de una página: si no cabe
al menos el comienzo del texto que les sigue, pasan a la página siguiente.

### Títulos de nivel 3

No saltes niveles: un `###` debe ir dentro de un `##`. El comando `check` avisa si
encuentra un salto.

#### Títulos de nivel 4

El nivel 4 es el más pequeño. Sirve para subdividir una sección larga.

## Formato dentro del texto

Un párrafo puede llevar **negrita**, *cursiva*, ***las dos a la vez***, ~~tachado~~,
`código en línea` y [enlaces](https://github.com). Para forzar un salto de línea
dentro del mismo párrafo,
deja dos espacios al final de la línea anterior.

Los párrafos se separan con una línea en blanco. El texto se justifica a la izquierda y
se separa en sílabas al final de línea cuando hace falta.

# Listas

## Lista con viñetas

- Primer elemento
- Segundo elemento, con **formato** dentro
  - Un elemento anidado: dos espacios de sangría
  - Otro elemento anidado
    - Tercer nivel
- Tercer elemento

## Lista numerada

1. Primer paso
2. Segundo paso
   1. Subpaso numerado: tres espacios de sangría
   2. Otro subpaso
3. Tercer paso

Una lista numerada puede empezar en cualquier número:

5. Este elemento es el quinto
6. Y este el sexto

# Tablas

Una tabla se escribe con barras verticales. La segunda fila define la alineación:
`:--` a la izquierda, `:-:` centrada y `--:` a la derecha. Para que la tabla lleve un
número y un pie, escribe un párrafo que empiece con `Tabla:` justo antes de ella.

Tabla: Ejemplo con alineaciones y celdas vacías

| Producto | Categoría | Stock | Precio |
|:--|:-:|--:|--:|
| Teclado mecánico | Periféricos | 14 | 89,90 |
| Monitor 27" | Pantallas | 3 | 329,00 |
| Cable USB-C | | 120 | 9,50 |
| Base para portátil | Accesorios | | 34,00 |

El encabezado va en negrita y, si la tabla no cabe en una página, se repite arriba de
cada página por la que continúa.

Tabla: Una tabla sin pie no lleva número; esta sí, porque tiene el párrafo «Tabla:»

| Sin pie | Con pie |
|---|---|
| No se numera | Se numera: «Tabla N.» |

# Código

Un bloque de código va entre tres comillas invertidas. La palabra después de las
comillas indica el lenguaje y aparece como etiqueta encima del bloque.

```python
def saludar(nombre: str) -> str:
    """Devuelve un saludo."""
    return f"Hola, {nombre}"
```

```bash
python -m genpdf build mi-documento
```

Si el código contiene tres comillas invertidas, abre y cierra el bloque con cuatro:

````markdown
```js
console.log("esto es Markdown dentro de un bloque de código");
```
````

El código en línea va entre comillas invertidas simples: `npm install`. Si contiene
una comilla invertida, usa dos como delimitador: `` `así` ``.

# Imágenes

Una imagen sola en su párrafo se convierte en una figura numerada. El pie sale del
título (el texto entre comillas) y, si no hay título, del texto alternativo.

![Diagrama del flujo de genpdf](img/diagram.svg "Este es el pie de la figura")

La ruta es relativa a la carpeta donde está el `.md`. Las imágenes se ajustan al ancho
útil de la página. Se admiten PNG, JPG y SVG.

# Citas y separadores

> Una cita se escribe empezando la línea con `>`.
>
> Puede tener varios párrafos y también **formato**.

Una línea con tres guiones dibuja un separador horizontal:

---

Y el texto continúa después del separador.

# Saltos de página y HTML

Para forzar un salto de página, escribe en una línea sola el comentario
`<!-- pagebreak -->`. Los demás comentarios HTML no salen en el PDF: sirven como notas
para quien edita.

<!-- Esta nota no aparece en el PDF. -->

Si Markdown no alcanza, puedes escribir HTML directamente y pasa tal cual al PDF:

<p style="padding: 10pt 14pt; border: 1pt solid #d1d9e0; border-radius: 4pt; background: #f6f8fa;">
Este recuadro está escrito en <strong>HTML</strong>, con estilos propios.
</p>

<!-- pagebreak -->

# Lo que revisa el validador

El comando `python -m genpdf check` revisa sin generar nada:

- Que el frontmatter tenga `type` y `title`, con los tipos correctos.
- Que no quede texto de relleno: `lorem ipsum` o las palabras `TODO` y `XXX` en
  mayúsculas. Dentro de bloques de código no cuentan.
- Que todas las imágenes existan en disco.
- Que no haya saltos de nivel entre títulos.
- Que, con `toc: true`, haya al menos un título de nivel 1.
