# Release Checklist

Cette checklist sert de fil conducteur pour publier une nouvelle stable
Windows sans oublier les points sensibles de version, packaging et changelog.

## Preparation

1. Aligner la version dans :
   - `astroclocks/version.py`
   - `pyproject.toml`
   - `AstroClocks-v3.3.iss`
   - `README.md`
   - `CHANGELOG.md`
2. Verifier que le changelog commence bien par la nouvelle section stable.
3. Verifier que l'executable distribue garde le bon nom fixe :
   - `AstroClockV3.exe`

## Validation locale

1. Lancer la suite de tests :

   ```powershell
   .\.venv\Scripts\python.exe -m unittest discover -s tests -v
   ```

2. Regenerer les artefacts Windows :

   ```powershell
   .\Build-Windows.ps1
   ```

3. Verifier la coherence release + packaging :

   ```powershell
   .\Verify-Release.ps1
   ```

## Smoke tests conseilles

1. Lancer `output\AstroClockV3\AstroClockV3.exe`.
2. Verifier l'ouverture de `Parametres` et `A propos`.
3. Verifier la carte du ciel et la recherche rapide.
4. Si une monture est disponible, verifier connexion, deconnexion et reticule.
5. Si un installeur precedent existe, verifier l'upgrade avec
   `installer\Install_AstroClocks<version>.exe`.

## Publication

1. Committer la release.
2. Creer ou mettre a jour le tag `vX.Y.Z-stable`.
3. Pousser la branche de maintenance et `main`.
4. Creer la GitHub Release avec le texte du changelog.
5. Attacher l'installeur versionne `Install_AstroClocks<version>.exe`.
