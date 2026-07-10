# MOTION_AND_INTERACTION.md

Contrato de motion, efectos visuales e interacciones para NODO.

## Objetivo

NODO debe sentirse vivo, rapido y premium dentro de Telegram. Las pantallas no deben verse estaticas, pero las animaciones no pueden distraer, degradar performance ni romper la sensacion nativa de Mini App.

## Regla madre

Toda animacion debe apoyar una accion, un estado o una transicion. No se permiten efectos decorativos pesados sin funcion.

## Herramientas permitidas

- CSS transitions/keyframes para microinteracciones simples.
- Framer Motion solo si el bundle/performance se mantiene aceptable.
- Telegram haptics para acciones criticas definidas en `TELEGRAM_MINI_APP_RULES.md`.
- `@telegram-apps/telegram-ui` para componentes base.

Builder debe evitar librerias grandes de animacion si CSS o Framer Motion resuelve el caso.

## Logo animado

La pantalla de entrada debe tener un `AnimatedLogo` o componente equivalente.

Comportamiento esperado:

- logo aparece con fade-in suave
- N/wordmark tiene small scale-in controlado
- check/verification accent puede hacer pulse breve
- flecha/acento verde puede tener movimiento corto ascendente o shine sutil
- duracion total objetivo: 900ms a 1400ms
- despues de la entrada, el logo queda estable

No permitido:

- loop infinito llamativo
- giro 3D exagerado
- bounce infantil
- efecto crypto/web3
- particulas pesadas
- canvas obligatorio solo para logo
- animacion que retrase carga real

## Pantalla de inicio

La home no debe sentirse estatica.

Debe incluir:

- entrada escalonada del header, card principal y secciones
- amount card con foco visual suave
- CTA con gradiente vivo y feedback de presion
- cards de marketplace con hover/press/tap state
- skeleton loading con shimmer sutil mientras carga data remota

Duraciones recomendadas:

```txt
screen enter: 180ms - 260ms
card enter stagger: 40ms - 80ms
button press: 90ms - 140ms
logo intro: 900ms - 1400ms
skeleton shimmer: 1200ms - 1800ms
```

## Microinteracciones obligatorias

- botones: pressed state
- tabs: active transition
- cards seleccionables: tap/press feedback
- segmented controls: active indicator transition
- inputs: focus border transition
- verified badge: static by default, pulse only during entry or verification success
- timers: cambio visual cuando entra en warning/critical
- success actions: haptic + short visual confirmation
- errors: no shake agresivo; usar borde/error text claro

## Transiciones de pantalla

Permitidas:

- fade + translateY corto
- shared shell estable
- content swap suave

No permitido:

- page transitions lentas
- full-screen loaders innecesarios
- animaciones que bloquean navegacion
- saltos de layout

## Performance

Requisitos:

- usar transform/opacity para animaciones principales
- evitar animar width/height/top/left si causa reflow
- respetar `prefers-reduced-motion`
- mantener 60fps objetivo en dispositivos medios
- no cargar assets pesados para efectos decorativos
- no usar video de fondo en MVP

## Accesibilidad

Si el usuario tiene reduced motion:

- desactivar logo motion complejo
- mantener fade simple max 150ms
- desactivar shimmer continuo
- mantener feedback visual no animado

## QA visual obligatorio

Builder debe verificar:

- desktop/mobile viewport de desarrollo
- Telegram Mini App viewport cuando sea posible
- no hay texto solapado
- no hay layout shift por animaciones
- no hay animaciones infinitas molestas
- reduced motion funciona
- logo termina en estado estable

## Evidencia requerida

Todo slice que cree pantallas debe reportar:

- componentes animados agregados
- duraciones usadas
- estados reduced motion
- captura o descripcion de verificacion visual
- razon si no aplica motion en una pantalla

