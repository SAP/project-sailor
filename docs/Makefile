# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = sphinx-build
SPHINXPROJ    = sailor
SOURCEDIR     = .
BUILDDIR      = _build

APIDOC_TEMPLATEDIR = _templates/apidoc
APIDOC_OUTDIR = apidoc
APIDOC_SOURCEDIR = ../sailor

.PHONY: apidoc
apidoc:
	@SPHINX_APIDOC_OPTIONS="members" sphinx-apidoc -e -f --templatedir "$(APIDOC_TEMPLATEDIR)" -o "$(APIDOC_OUTDIR)" "$(APIDOC_SOURCEDIR)"

.PHONY: Makefile
html:
	@$(SPHINXBUILD) -b html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)
