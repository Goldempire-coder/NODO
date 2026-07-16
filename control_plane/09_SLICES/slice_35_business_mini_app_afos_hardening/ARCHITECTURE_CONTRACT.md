# ARCHITECTURE_CONTRACT.md

## Principio

La Mini App Negocio debe tener arquitectura limpia: pantalla muestra, hook coordina, API client transporta, backend decide reglas sensibles.

## Reglas

- `useBusinessMiniAppModel.ts` debe seguir siendo ensamblador.
- Ningun hook debe mezclar demasiadas responsabilidades sin excepcion documentada.
- La logica de dominio sensible no debe vivir solo en componentes React.
- Las pantallas no deben contener reglas financieras.
- Los helpers puros de presentacion deben estar fuera de hooks con efectos.
- Los API clients no deben contener UI copy ni reglas de negocio.
- Los errores de PIN deben tener fuente comun.
- Los estados de botones deben ser por accion, no por busy global, cuando afecten acciones independientes.

## Umbrales de revision

Builder debe reportar lineas antes/despues de:

- `useBusinessAccessModel.ts`
- `useBusinessAdsModel.ts`
- `useBusinessCreditsModel.ts`
- `BusinessAdsScreens.tsx`
- `BusinessCreditsScreens.tsx`
- `BusinessMiniAppShell.tsx`

Objetivo recomendado:

- hooks de dominio menores a 250 lineas o excepcion justificada;
- componentes de pantalla mayores a 250 lineas deben dividirse si tienen responsabilidades mezcladas;
- funciones async de accion sensible deben ser legibles y con errores controlados.

Estos umbrales no son cosmeticos. Se usan para evitar que el modulo vuelva a ser dificil de corregir.

## Evidencia aceptable

- diff;
- line count antes/despues;
- tests estaticos que protejan separacion;
- build web;
- reporte de riesgos si un archivo grande queda por decision consciente.
