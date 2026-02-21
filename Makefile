.PHONY: duo-cats-sources duo-cats-build duo-cats-gifs duo-cats-contact-sheet duo-cats-validate duo-cats-all

duo-cats-sources:
	python scripts/generate_duo_cat_sources.py --debug --verbose

duo-cats-build:
	python scripts/build_duo_cat_atlases.py

duo-cats-gifs:
	python scripts/export_duo_cat_gifs.py

duo-cats-contact-sheet:
	python scripts/build_duo_cat_contact_sheet.py

duo-cats-validate:
	python scripts/validate_duo_cat_pack.py

duo-cats-all: duo-cats-sources duo-cats-build duo-cats-gifs duo-cats-validate
