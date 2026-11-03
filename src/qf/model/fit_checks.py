"""Un ajuste fallido no se publica ni se convierte en un modelo válido por tener coeficientes."""
import numpy as np


class AjusteNoConvergente(RuntimeError):
    pass


def validar_ajuste(resultado, nombre: str) -> dict:
    diagnostico = {'success': bool(resultado.success), 'message': str(resultado.message),
                  'iterations': int(getattr(resultado, 'nit', 0)), 'objective': float(resultado.fun)}
    if not resultado.success or not np.isfinite(resultado.fun) or not np.isfinite(resultado.x).all():
        raise AjusteNoConvergente(f'{nombre}: {diagnostico}')
    return diagnostico
