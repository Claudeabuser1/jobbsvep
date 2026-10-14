# Matchd as an app

There are two steps. Step 1 is already built and live. Step 2 is set up and ready, and needs your developer accounts.

## Step 1: installable web app (done)

The website is a Progressive Web App:

- `web/manifest.webmanifest` and `web/manifest.en.webmanifest` give it a name, icon and colours, and tell the phone to open it full screen without browser bars.
- `web/sw.js` (service worker) keeps a copy of the app and the last loaded job list, so it opens even without internet. Pages and job data always try the network first, so nothing goes stale while online. The AI server is never cached.
- Icons are in `web/icons/`. The original is `icon.svg`; the PNGs were made from it.

How a user installs it:

- **iPhone (Safari):** open the site, tap Share, then "Lägg till på hemskärmen".
- **Android (Chrome):** open the site and tap "Installera app" in the menu, or the banner Chrome shows.

This costs nothing and needs no app store. Use it to test whether people actually keep Matchd on their phones before paying for store accounts.

## Step 2: real iPhone and Android apps (ready, not built)

`app/` wraps the same web code in a native app with [Capacitor](https://capacitorjs.com). There is one codebase: everything you change in `web/jobbsvep.html` shows up on the website and in both apps.

How it fits together:

```
web/jobbsvep.html ──build_site.py──► site/ ──npm run web──► app/www/ ──Capacitor──► iOS app / Android app
                                        │
                                        └──► GitHub Pages (website)
```

The app build sets `APP_DATA_BASE` so the app loads the job list from the live website. The list stays fresh twice a week without publishing app updates. GitHub Pages allows this (it sends `access-control-allow-origin: *`).

### What you need

| | iPhone | Android |
| --- | --- | --- |
| Computer | A Mac with Xcode (free from the App Store) | Any computer with Android Studio (free) |
| Developer account | Apple Developer Program, 99 USD per year | Google Play Console, 25 USD once |
| Test device | Your iPhone, or the simulator in Xcode | Your Android phone, or the emulator |

### Build it the first time

```bash
cd app && npm install
```

```bash
npx cap add ios && npx cap add android
```

```bash
npm run ios
```

```bash
npm run android
```

`npm run ios` and `npm run android` build the site, copy it into the app and open Xcode or Android Studio. Press Run there to start the app on a phone or simulator.

### Before the first store release

1. **Let the app call the AI server.** Inside the app, the page's address is `capacitor://localhost` (iPhone) or `https://localhost` (Android). Add both to `ALLOWED_ORIGINS` in `server/fly.toml`, then run `fly deploy`.
2. **Decide how to sell plans in the app.** Apple and Google generally require their own in-app purchase system for digital services bought inside an app, and they take 15–30%. The options are:
   - Keep paid plans on the website only. The app shows free features and AI credits the user already has.
   - Add in-app purchases. Raise app prices or lower AI budgets so the PRICING.md guarantee still holds after the store's cut.

   Check the current rules for your region when you get there: the EU rules (DMA) have been changing.
3. **Give the app something the website can't do.** Stores can reject apps that are just a website in a frame. The best candidates for Matchd:
   - **Push notifications:** "3 new jobs within 2 km of you". Uses `@capacitor/push-notifications` plus a small addition to the server.
   - **"Near me" with GPS** instead of typing an address: `@capacitor/geolocation`.
   - **Haptic feedback** on swipes: `@capacitor/haptics`.
4. **Store listing.**
   - Screenshots and a short description, in Swedish and English.
   - A privacy policy URL: the help page.
   - An age rating. Users are 16+, but the app has no adult content, so it will likely get the lowest or a teen rating.
   - The "delete my data" requirement is already covered by the help page.
5. **App ID.** `app/capacitor.config.json` uses `se.matchd.app`, based on the domain matchd.se. It can never be changed after the first upload, so buy matchd.se before you publish.

## What I did not do

I did not run `npm install` or create the `ios/` and `android/` projects. Those are large, machine-specific folders, and you need Xcode or Android Studio to open them anyway. The configuration in `app/` is valid JSON and follows Capacitor 8's format, but it has not been built yet.
