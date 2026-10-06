# Third-party dependencies

The MIT license in this repository covers RuCorpus code and documentation. It does not relicense dependencies, NLP model/dictionary distributions, fonts or user-provided data. Python dependencies are installed from `backend/requirements.txt`; JavaScript dependencies are recorded in `frontend/package-lock.json`. Preserve the licenses and notices included in those distributions, including transitive packages and model resources.

Key projects include [Django](https://github.com/django/django), [django-ninja](https://github.com/vitalik/django-ninja), [pymorphy3](https://github.com/no-plagiarism/pymorphy3), [pymorphy dictionaries](https://github.com/kmike/pymorphy2-dicts), [Natasha](https://github.com/natasha/natasha), [jieba](https://github.com/fxsjy/jieba), [openpyxl](https://openpyxl.readthedocs.io/), [WhiteNoise](https://github.com/evansd/whitenoise), [Waitress](https://github.com/Pylons/waitress), [Vue](https://github.com/vuejs/core), [Vite](https://github.com/vitejs/vite), [Tailwind CSS](https://github.com/tailwindlabs/tailwindcss), [Lucide](https://github.com/lucide-icons/lucide), [VueUse](https://github.com/vueuse/vueuse) and [Pinia](https://github.com/vuejs/pinia).

The frontend bundles Inter, Source Serif 4 and JetBrains Mono through Fontsource packages. Their SIL Open Font License notices and Lucide's icon license are included in `frontend/public/licenses/` and copied into built assets. Retain these notices when redistributing built assets.

No external corpus, annotation dataset, reference text or optional Chinese idiom list is distributed here. If `RUCORPUS_IDIOMS_PATH` is configured, the operator is responsible for the resource's provenance and permitted use.
