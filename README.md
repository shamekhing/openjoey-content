# openjoey-content

All runtime content for the OpenJoey split: `cards.json` (schema owned by the
cards repo's CardParser), `settings.json`, `decks/` (format owned by the app
repo's deck editor), and `data/images/` (fetched by CardImageCache via URLs
from Settings).

data/images/ is gitignored (regenerable; monorepo policy kept). At build time
openjoey-app symlinks this data/ next to the binary so runtime paths are
unchanged: <builddir>/data/...
