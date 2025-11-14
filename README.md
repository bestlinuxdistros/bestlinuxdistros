# 🐧 BestLinuxDistros — Modern Linux Distribution Directory

A fully open-source, neon-styled hub for discovering, comparing, and understanding Linux distributions.  
Powered by one JSON dataset, a static generator, and beautiful UI inspired by hacker aesthetics.

🌐 **Website:** https://bestlinuxdistros.com  
📦 **Open-source project:** Made by Saif

---

## 🔥 Features

### ✔ Curated Linux distribution profiles
Every distro page includes:
- Real descriptions  
- Pros & cons  
- Hardware requirements  
- Package manager explanation  
- Benchmarks & scores  
- User audience (Beginner, Developer, Gamer…).  
- Screenshots (Wikipedia API)  
- Related distros  
- Download buttons & official website links  
- JSON-LD schema + Open Graph cards  

### ✔ Real-time static generation
One command rebuilds:
- `/distros/*.html` pages  
- `/assets/og/*.png` Open Graph images  
- `/js/distro-data.js` snapshot  
- `/sitemap.xml`  

### ✔ Modern UI / UX
- Neon hacker theme  
- Floating glass navigation  
- Typewriter hero  
- Responsive grids  
- Lightbox screenshots  
- Compare up to 4 distros  
- Offline-ready dataset via localStorage  

### ✔ Blog, Guides & Tools  
- `/blog/` full SEO-optimized articles  
- `/guides/` high-value tutorials  
- `/tools/` static tools & reference sheets  

---

## 📂 Project Structure

```
bestlinuxdistros/
│ index.html
│ distros.html
│ compare.html
│ sitemap.xml
│ robots.txt
│
├── api/
│   └── linux_distros_full.json
│
├── distros/
│   └── <id>.html        # generated detail pages
│
├── blog/
│   ├── index.html
│   ├── best-linux-distros-for-beginners-2025.html
│   ├── best-linux-distros-for-developers-2025.html
│   └── best-lightweight-linux-distros-for-old-laptops-2025.html
│
├── guides/
│   └── *.html   
│
├── tools/
│   └── *.html  
│
├── css/
│   └── styles.css
│
├── js/
│   ├── app.js
│   ├── detail.js
│   └── distro-data.js
│
└── tools/
    └── build_distros.py   # static generator
```

---

## 🚀 Getting Started

### 1. Clone the repo
```bash
git clone https://github.com/saifdev404/bestlinuxdistros.git
cd bestlinuxdistros
```

### 2. Install Python dependencies
(Optional but recommended for OG image generation)

```bash
pip install pillow
```

### 3. Generate all distro pages
```bash
cd tools
python build_distros.py
```

This updates:
- distros/*.html  
- js/distro-data.js  
- sitemap.xml  
- assets/og/<id>.png (Open Graph images)  

### 4. Run a local server
Static:

```bash
python -m http.server 8000
```

Open:
```
http://localhost:8000
```

---

## 🧠 How the Data Works

All distro info lives inside:

```
api/linux_distros_full.json
```

Each object contains:

```json
{
  "id": "ubuntu",
  "name": "Ubuntu",
  "family": "Debian-based",
  "download_url": "https://ubuntu.com/download",
  "badges": ["Beginner-friendly", "Secure", "Great for developers"],
  "screenshots": ["https://..."],
  ...
}
```

You can edit this file to add/remove distros, then rebuild.

---

## 🛠 Contributing

Pull requests are welcome!

If you want to:

- Add a new distro  
- Add screenshots  
- Add a new guide or tool  
- Improve performance or UX  
- Fix typos / metadata  

Feel free to open an issue or PR.

---

## 📌 Roadmap

- [ ] Interactive Tools (hardware checker, distro quiz)
- [ ] Auto-update data via live APIs
- [ ] More guides (gaming, servers, WM vs DE)
- [ ] Benchmark automation
- [ ] Dark/light theme toggle
- [ ] Community suggestions

---

## 📄 License

MIT License — free to modify, reuse, or contribute.

---

## 📣 Social & Branding

**Social preview description:**

> BestLinuxDistros — A modern neon-themed hub for discovering and comparing Linux distributions. Real screenshots, benchmarks, hardware requirements, and open-source tools.

---

## ❤️ Credits

Made by **Saif**  
Open-source forever.
