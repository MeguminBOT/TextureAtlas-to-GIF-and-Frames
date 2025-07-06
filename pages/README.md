# GitHub Pages Site for TextureAtlas to GIF and Frames

This directory contains the GitHub Pages website for the TextureAtlas to GIF and Frames project.
This site will be the replacement for regular users that are less likely to read the documentations in the repository.
Site is still work in progress.

Any contribution commits made related to the github pages site should be prefixed with "[Pages]" in the commit name.

## 🎨 Features

### Design
- **Material Design colors** for both light and dark themes
- **Responsive design** that works on all devices
- **Dark mode support** with system preference detection and manual toggle
- **Modern, professional layout** with smooth animations

### Theme System
- **Default to dark mode**
- **System theme detection**
- **Manual toggle** with keyboard support (🌙/☀️ button)
- **Persistent user preferences**

### Technical
- **Pure HTML/CSS/JS** - no build tools required
- **SEO optimized** with proper meta tags
- **Accessibility features** with ARIA labels and focus states
- **Fast loading** with optimized CSS and minimal dependencies

## 🔧 Customization

### Colors
All colors are defined as CSS custom properties in `css/style.css`:
- Light theme: Material Design standard colors
- Dark theme: Material Design dark variants
- Modify the `:root` and `[data-theme="dark"]` sections to change colors

### Content
- Edit HTML files directly to update content
- Add new pages by creating additional HTML files
- Update navigation links in all HTML files

### Styling
- Custom styles are in `css/style.css`
- Uses CSS Grid and Flexbox for responsive layouts
- Material Design color system and spacing

## 📝 Adding New Pages

1. Create a new HTML file (e.g., `new-page.html`)
2. Copy the structure from `index.html` or `download.html`
3. Update the `<title>` and content
4. Add navigation links to all existing HTML files
5. Update the active link styling

## � Deployment

### Automatic Deployment (Recommended)
The site uses GitHub Actions for automatic deployment:
- Push changes to the main branch
- GitHub Actions builds and deploys automatically
- Available at your GitHub Pages URL

## 🤝 Contributing

To contribute to the website:
1. Edit the HTML files directly
2. Test locally using a simple HTTP server
3. Submit a pull request with your changes

## � License
This website is part of the TextureAtlas to GIF and Frames project and follows the same license terms.


*This site showcases the TextureAtlas to GIF and Frames project and provides comprehensive documentation for users and developers.*
