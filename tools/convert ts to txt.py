#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simple Translation Converter
============================

Converts simple text-based translation files to Qt .ts format.

Text format:
original := translated

Example:
Language Settings := Språkinställningar
Select Application Language := Välj applikationsspråk
"""

import xml.etree.ElementTree as ET
from pathlib import Path
import argparse


class SimpleTranslationConverter:
    """Converts simple text translation files to Qt .ts format."""
    
    def __init__(self, project_root=None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent
        self.translations_dir = self.project_root / "src" / "translations"
        self.simple_translations_dir = self.project_root / "translations"
        
    def ensure_directories(self):
        """Ensure the necessary directories exist."""
        self.simple_translations_dir.mkdir(exist_ok=True)
        self.translations_dir.mkdir(exist_ok=True)
        
    def parse_simple_translation_file(self, file_path):
        """
        Parse a simple translation file.
        
        Args:
            file_path (Path): Path to the simple translation file
            
        Returns:
            dict: Dictionary mapping original strings to translations
        """
        translations = {}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#') or line.startswith('//'):
                    continue
                    
                # Parse the format: original := translated
                if ':=' in line:
                    parts = line.split(':=', 1)
                    if len(parts) == 2:
                        original = parts[0].strip()
                        translated = parts[1].strip()
                        
                        if original and translated:
                            translations[original] = translated
                        else:
                            print(f"Warning: Empty original or translation on line {line_num}: {line}")
                    else:
                        print(f"Warning: Invalid format on line {line_num}: {line}")
                else:
                    print(f"Warning: No ':=' separator found on line {line_num}: {line}")
                    
        return translations
        
    def load_ts_file(self, ts_file_path):
        """
        Load an existing .ts file.
        
        Args:
            ts_file_path (Path): Path to the .ts file
            
        Returns:
            ET.ElementTree: Parsed XML tree
        """
        if not ts_file_path.exists():
            print(f"Warning: {ts_file_path} does not exist")
            return None
            
        try:
            tree = ET.parse(ts_file_path)
            return tree
        except ET.ParseError as e:
            print(f"Error parsing {ts_file_path}: {e}")
            return None
            
    def apply_translations_to_ts(self, ts_tree, translations):
        """
        Apply translations from simple format to .ts file.
        
        Args:
            ts_tree (ET.ElementTree): Parsed .ts file
            translations (dict): Dictionary of translations
            
        Returns:
            int: Number of translations applied
        """
        if not ts_tree:
            return 0
            
        root = ts_tree.getroot()
        applied_count = 0
        
        # Find all message elements
        for context in root.findall('context'):
            for message in context.findall('message'):
                source_elem = message.find('source')
                translation_elem = message.find('translation')
                
                if source_elem is not None and translation_elem is not None:
                    source_text = source_elem.text
                    
                    if source_text in translations:
                        # Apply the translation
                        translation_elem.text = translations[source_text]
                        
                        # Remove any 'type="unfinished"' attribute
                        if 'type' in translation_elem.attrib:
                            if translation_elem.attrib['type'] == 'unfinished':
                                del translation_elem.attrib['type']
                                
                        applied_count += 1
                        print(f"Applied: '{source_text}' -> '{translations[source_text]}'")
                        
        return applied_count
        
    def save_ts_file(self, ts_tree, ts_file_path):
        """
        Save the .ts file with proper formatting.
        
        Args:
            ts_tree (ET.ElementTree): Tree to save
            ts_file_path (Path): Path to save to
        """
        # Format the XML properly
        ET.indent(ts_tree, space="    ")
        
        # Write with XML declaration
        with open(ts_file_path, 'wb') as f:
            ts_tree.write(f, encoding='utf-8', xml_declaration=True)
            
        print(f"Saved: {ts_file_path}")
        
    def create_example_translation_file(self, language_code):
        """
        Create an example simple translation file.
        
        Args:
            language_code (str): Language code (e.g., 'sv')
        """
        example_file = self.simple_translations_dir / f"{language_code}.txt"
        
        example_content = f"""# Simple Translation File for {language_code.upper()}
# Format: original := translated
# Lines starting with # are comments and will be ignored
#
# Example translations (replace with actual translations):

Language Settings := [TRANSLATE: Language Settings]
Select Application Language := [TRANSLATE: Select Application Language] 
Language: := [TRANSLATE: Language:]
Cancel := [TRANSLATE: Cancel]
Apply := [TRANSLATE: Apply]
Error := [TRANSLATE: Error]

# Multi-line strings can be written on one line:
Note: The application will need to restart to fully apply the language change. := [TRANSLATE: Note about restart]

# Quality indicators - keep the emoji symbols:
Quality indicators: ✅ Native, 👥 Community, 🤖 Machine, ⚠️ Partial := [TRANSLATE: Quality indicators explanation]

# You can add more translations here...
# To find all translatable strings, check the existing app_{language_code}.ts file
"""
        
        with open(example_file, 'w', encoding='utf-8') as f:
            f.write(example_content)
            
        print(f"Created example translation file: {example_file}")
        return example_file
        
    def extract_strings_from_ts(self, ts_file_path, output_file):
        """
        Extract all translatable strings from a .ts file into simple format.
        
        Args:
            ts_file_path (Path): Path to the .ts file
            output_file (Path): Path for the output simple translation file
        """
        ts_tree = self.load_ts_file(ts_file_path)
        if not ts_tree:
            return
            
        root = ts_tree.getroot()
        strings = []
        
        # Extract all source strings
        for context in root.findall('context'):
            context_name = context.find('name')
            context_name_text = context_name.text if context_name is not None else "Unknown"
            
            strings.append(f"\n# Context: {context_name_text}")
            
            for message in context.findall('message'):
                source_elem = message.find('source')
                translation_elem = message.find('translation')
                
                if source_elem is not None:
                    source_text = source_elem.text or ""
                    
                    # Check if already translated
                    if translation_elem is not None and translation_elem.text:
                        # Already translated
                        translation_text = translation_elem.text
                        strings.append(f"{source_text} := {translation_text}")
                    else:
                        # Not translated - add placeholder
                        strings.append(f"{source_text} := [TRANSLATE: {source_text}]")
                        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Simple Translation File\n")
            f.write(f"# Generated from: {ts_file_path.name}\n")
            f.write("# Format: original := translated\n")
            f.write("#\n")
            f.write("# Instructions:\n")
            f.write("# 1. Replace [TRANSLATE: ...] with actual translations\n")
            f.write("# 2. Keep the format: original := translated\n")
            f.write("# 3. Save and run the converter to apply changes\n\n")
            
            for string in strings:
                f.write(string + '\n')
                
        print(f"Extracted {len([s for s in strings if ':=' in s])} strings to: {output_file}")
        
    def convert(self, language_code, create_example=False, extract_mode=False):
        """
        Convert simple translation file to .ts format.
        
        Args:
            language_code (str): Language code (e.g., 'sv')
            create_example (bool): Whether to create an example file
            extract_mode (bool): Whether to extract strings from .ts to simple format
        """
        self.ensure_directories()
        
        simple_file = self.simple_translations_dir / f"{language_code}.txt"
        ts_file = self.translations_dir / f"app_{language_code}.ts"
        
        if extract_mode:
            self.extract_strings_from_ts(ts_file, simple_file)
            return
            
        if create_example:
            self.create_example_translation_file(language_code)
            return
            
        if not simple_file.exists():
            print(f"Simple translation file not found: {simple_file}")
            print("Use --create-example to create an example file")
            return
            
        # Parse the simple translation file
        print(f"Loading translations from: {simple_file}")
        translations = self.parse_simple_translation_file(simple_file)
        print(f"Found {len(translations)} translations")
        
        if not translations:
            print("No translations found in the file")
            return
            
        # Load the .ts file
        print(f"Loading .ts file: {ts_file}")
        ts_tree = self.load_ts_file(ts_file)
        
        if not ts_tree:
            print(f"Could not load .ts file: {ts_file}")
            return
            
        # Apply translations
        print("Applying translations...")
        applied_count = self.apply_translations_to_ts(ts_tree, translations)
        
        if applied_count > 0:
            # Save the updated .ts file
            self.save_ts_file(ts_tree, ts_file)
            print(f"\nSuccess! Applied {applied_count} translations to {ts_file}")
        else:
            print("No translations were applied")


def main():
    parser = argparse.ArgumentParser(
        description="Convert simple translation files to Qt .ts format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create an example translation file for Swedish
  python simple_translation_converter.py sv --create-example
  
  # Extract strings from .ts file to simple format for translation
  python simple_translation_converter.py sv --extract
  
  # Apply translations from simple file to .ts file
  python simple_translation_converter.py sv
  
  # Process multiple languages
  python simple_translation_converter.py sv es fr de
        """
    )
    
    parser.add_argument('languages', nargs='+', help='Language codes to process (e.g., sv es fr)')
    parser.add_argument('--create-example', action='store_true', 
                       help='Create example translation files')
    parser.add_argument('--extract', action='store_true',
                       help='Extract strings from .ts files to simple format')
    parser.add_argument('--project-root', help='Path to project root directory')
    
    args = parser.parse_args()
    
    converter = SimpleTranslationConverter(args.project_root)
    
    for language_code in args.languages:
        print(f"\n{'='*50}")
        print(f"Processing language: {language_code}")
        print(f"{'='*50}")
        
        converter.convert(
            language_code, 
            create_example=args.create_example,
            extract_mode=args.extract
        )


if __name__ == '__main__':
    main()
