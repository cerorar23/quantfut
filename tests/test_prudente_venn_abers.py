import numpy as np

from qf.eval.prudente_venn_abers import venn_abers_bajo


def test_venn_abers_bajo_esta_en_rango_y_crece_con_la_probabilidad():
    rng = np.random.default_rng(2)
    p = rng.uniform(0.1, 0.9, 800)
    y = (rng.uniform(size=800) < p).astype(float)
    bajo = venn_abers_bajo(p, y, np.array([0.2, 0.5, 0.8]))
    assert ((0 <= bajo) & (bajo <= 1)).all()
    assert bajo[0] < bajo[1] < bajo[2]
    assert abs(bajo[1] - 0.5) < 0.1
