"""College football modeling system. Specification: docs/blueprint/."""

import os

# One BLAS/OpenMP thread per process unless the caller sets these explicitly: heavy fits
# otherwise spread over every core. Set before any submodule imports numpy.
for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_var, "1")

__version__ = "0.0.1"
