import json
import logging

try:
    from hola import crear_mapa_calificaciones
    # Hack the input to always be the sheet number (16 for CALIF. 3ER TRIM.)
    import builtins
    builtins.input = lambda x: '16'
    
    import sys, os
    old_stdout = sys.stdout
    sys.stdout = open(os.devnull, 'w')
    mapa = crear_mapa_calificaciones('sb2.xlsx')
    sys.stdout.close()
    sys.stdout = old_stdout
    
    # Let's print the first few relevant notes
    count = 0
    for est, notas in mapa.items():
        if count >= 10: break
        print(f"{est} | LENGUA: {notas.get('LENGUA Y LITERATURA')} | ANIM: {notas.get('ANIMACIÓN A LA LECTURA')}")
        count += 1
except Exception as e:
    logging.exception(e)
