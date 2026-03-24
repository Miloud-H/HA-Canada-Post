# 📬 Canada Post - My Mail for Home Assistant

A custom integration for Home Assistant that tracks mail and circulars received via the Canada Post **"My Mail"** (Mon Courrier) service. Unlike integrations based on email scraping, this integration uses the official mobile API to extract real sender logos, delivery dates, and specific mailpiece details.

## Features
* **Zero-Config Discovery:** Automatically retrieves your unique `topic_id` via a GraphQL handshake—no manual log digging required.
* **Rich Media Support:** Displays actual sender logos (Metro, Raddar, Pizza Pizza, etc.) directly in your dashboard.
* **Smart Filtering:** Built-in option to include or exclude circulars/flyers (ServiceType 25).
* **Ecosystem Ready:** Uses standard `Mail and Packages` data structures (the `packages` attribute) for maximum compatibility with community cards.
* **Fully Localized:** Support for English and French.

## ⚠️ Prerequisite / Prérequis
Before installing this integration, you **must** have the "My Mail" (Mon Courrier) service activated on your Canada Post account.
1. Download the official Canada Post app.
2. Sign up or log in.
3. Activate the **"My Mail"** service (you will receive a verification code by physical mail to confirm your address).
*Note: If you don't see your mail in the official app, it won't appear in Home Assistant.*

---

Avant d'installer cette intégration, vous **devez** avoir activé le service "Mon Courrier" sur votre compte Postes Canada.
1. Téléchargez l'application officielle de Postes Canada.
2. Connectez-vous ou créez un compte.
3. Activez le service **"Mon Courrier"** (vous recevrez un code de vérification par la poste pour confirmer votre adresse).
*Note : Si vous ne voyez pas votre courrier dans l'application officielle, il n'apparaîtra pas dans Home Assistant.*

## 🔢 Entities Created
This integration creates three main sensors:
- `sensor.canada_post_delivered`: Detailed list of received mail.
- `sensor.canada_post_in_transit`: Count of mail currently on its way.
- `sensor.canada_post_mail_updated`: A compatibility sensor matching the "Mail and Packages" standard.

## 🚀 Installation

### Via HACS (Recommended)
1. In **HACS**, go to the **Integrations** section.
2. Click the three dots in the top right corner > **Custom repositories**.
3. Add the URL of this repository with the category `Integration`.
4. Click **Install**.
5. Restart Home Assistant.
6. Go to **Settings** > **Devices & Services** > **Add Integration** > Search for **Canada Post**.

## 📊 Dashboard Configuration

To achieve the professional look seen in the screenshots, we highly recommend using the [flex-table-card](https://github.com/custom-cards/flex-table-card).

### Example Lovelace Card:
```yaml
type: custom:flex-table-card
title: "📬 Canada Post - Recent Mail"
entities:
  - sensor.canada_post_delivered
columns:
  - name: ""
    data: packages
    modify: "x.image_url ? '<img src=\"' + x.image_url + '\" style=\"height: 25px; border-radius: 5px;\">' : '<ha-icon icon=\"mdi:email-outline\" style=\"--mdc-icon-size: 25px;\"></ha-icon>'"
    html: true
    width: 40px
  - name: Sender
    data: packages
    modify: x.sender
  - name: Date
    data: packages
    modify: x.estimated_delivery
    align: right
```

### Technical Details
This integration performs a secure authentication flow through Canada Post's AWS Cognito services. It utilizes a background DataUpdateCoordinator to poll the API hourly, ensuring your dashboard stays up to date without hitting rate limits.

## Compatibility with "Mail and Packages"
While this is a standalone integration, it maps its attributes to match the popular Mail and Packages standard.

* **Main Attribute**: packages
* **Sub-attributes**: sender, image_url, estimated_delivery, tracking_description.