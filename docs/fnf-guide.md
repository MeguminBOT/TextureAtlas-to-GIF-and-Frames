# Friday Night Funkin' Guide

Specialized guide for extracting and processing Friday Night Funkin' (FNF) character sprites and animations.
**This doc file was partly written by AI, some parts may need to be rewritten which I will do whenever I have time**

## 📑 Table of Contents

- [What is Friday Night Funkin'?](#-what-is-friday-night-funkin)
- [FNF Engine Support](#-fnf-engine-support)
- [FNF File Structure](#-fnf-file-structure)
  - [Example: Psych Engine JSON Structure](#example-psych-engine-json-structure)
- [Automatically loading FNF characters settings](#-automatically-loading-fnf-characters-settings)
- [FNF Animation Naming Conventions](#-fnf-animation-naming-conventions)
  - [Standard Animation Names](#standard-animation-names)
  - [Prefix Patterns](#prefix-patterns)
  - [Custom Naming](#custom-naming)
- [Known Bugs and Limitations](#-known-bugs--limitations)

## 🎵 What is Friday Night Funkin'?

Friday Night Funkin' (FNF) is a popular rhythm game with a vibrant modding community. Characters are typically stored as texture atlases with accompanying "Character data files" usually in JSON or XML format. These files define animation properties like scale, fps and more.

## 🎯 FNF Engine Support

This tool supports character data from multiple FNF engines:
- **Kade Engine** .json
- **Psych Engine**: .json
- **Codename Engine**: .xml

## 📁 FNF File Structure

**Most engines are structured similarly to this**
```
assets (or mod folder)
└── characters
    └── character.json
└── images/characters
    ├── character1.png
    └── character1.xml
```

### Example: Psych Engine JSON Structure

```json
{
    "animations": [
    {
        "name": "idle",
        "prefix": "BF idle dance",
        "fps": 24,
        "loop": false,
        "indices": [],
        "offsets": [0, 0]
    },
    {
        "name": "singLEFT",
        "prefix": "BF NOTE LEFT",
        "fps": 24,
        "loop": false,
        "indices": [],
        "offsets": [-5, -6]
        }
    ],
    "image": "character1",
    "scale": 1,
    "sing_duration": 6.1,
    "healthicon": "bf"
}
```

Please note that the following data is ignored and not needed by this tool:
```json
{
    "offsets"
    "healthicon"
    "sing_duration"
}
```

## 🚀 Automatically loading FNF characters settings

1. **Select directory with spritesheets** or **Menubar: Select files**
2. **Menubar: Import** → **FNF: Import settings from character data files**
3. **Show user settings** to confirm settings or double click an animation entry in the listbox to preview the output.


## 📋 FNF Animation Naming Conventions

### Standard Animation Names
- `idle` - Default standing/dancing animation
- `singLEFT`, `singDOWN`, `singUP`, `singRIGHT` - Note singing poses
- `singLEFTmiss`, `singDOWNmiss`, etc. - Missing note reactions
- `hey` - Special cheer/wave animation
- `scared` - Fear reaction (for GF characters)

### Prefix Patterns
Common prefixes found in XML metadata:
- `BF idle dance` → `idle`
- `BF NOTE LEFT` → `singLEFT`  
- `GF Dancing Beat` → `idle`
- `spooky dance idle` → `idle`

### Custom Naming
Use **Find/Replace Rules** to standardize naming:
- Find: `BF NOTE (LEFT|RIGHT|UP|DOWN)`
- Replace: `sing$1`
- Enable regex for pattern matching


## 🐞 Known Bugs & Limitations

### Indices, Loop problems or missing animations:
In cases where character data files containing several animations using the same **.xml**/**.txt** animation names but with different indices defined, only recognizes whatever the first entry is.

As an example, let's say you're trying to export `GF_assets` from Psych Engine and you're importing the `gf.json` file to get automated settings.

The JSON file contains `danceLEFT` and `danceRIGHT` which uses `GF Idle Dance` from the **.xml** file. The tool will in this case only export `danceLeft`. 

So you will need to manually remove the indices from that animation in the override settings window.

---

*For general usage instructions, see the [User Manual](user-manual.md). For technical issues, check the [FAQ](faq.md).* 