# DragTab

**Alt+Tab während des Ziehens – auch aus Thunderbird und anderen GTK-Programmen.**

[English version](README.md)

Wer unter X11 eine Mail aus Thunderbird zieht und dabei mit Alt+Tab zum
Zielfenster wechseln will, merkt: Es passiert nichts. Aus dem Dateimanager
klappt dasselbe problemlos.

Der Grund: GTK hält während des Ziehens die Tastatur fest. Der Fenstermanager
(Openbox, Xfwm, …) bekommt Alt+Tab deshalb gar nicht zu sehen. DragTab liest
die rohen XInput2-Ereignisse, die der X-Server trotzdem meldet, erkennt Alt+Tab
bei gedrückter linker Maustaste und holt das nächste Fenster nach vorn. Dort
lässt man die Mail einfach fallen.

- Das Fenster wechselt **sofort** beim Druck auf Tab, nicht erst beim Loslassen
  von Alt.
- Tab mehrmals drücken geht weiter, Shift+Alt+Tab geht zurück.
- Ohne Ziehen bleibt alles beim Alten – Alt+Tab macht weiter der
  Fenstermanager.
- DragTab greift nur bei den Programmen, die man ihm nennt (Standard:
  Thunderbird). So schaltet es bei Programmen, in denen Alt+Tab schon geht,
  nicht doppelt um.

## Voraussetzungen

- X11-Sitzung (unter Wayland kümmert sich der Compositor selbst ums Ziehen)
- ein Fenstermanager nach EWMH-Standard (Openbox, Xfwm, Marco, KWin, …)
- Python 3, `xdotool`, `xprop` und libXi

Unter Debian/Ubuntu:

```sh
sudo apt install python3 xdotool x11-utils libxi6
```

Getestet unter Ubuntu 22.04 mit LXQt und Openbox.

## Installation

```sh
git clone https://github.com/Codatus/dragtab.git
cd dragtab
./install.sh
```

Ohne git:

```sh
wget -qO- https://github.com/Codatus/dragtab/archive/refs/heads/main.tar.gz | tar xz && cd dragtab-main && ./install.sh
```

Das Skript installiert für den aktuellen Benutzer:

| Datei | Zweck |
|---|---|
| `~/.local/bin/dragtab` | das Programm |
| `~/.config/systemd/user/dragtab.service` | systemd-Benutzerdienst, startet nach Abstürzen neu |
| `~/.config/autostart/dragtab-start.desktop` | startet den Dienst bei der Anmeldung |

Der Start über die Autostart-Datei ist nötig, weil viele schlanke
Arbeitsumgebungen (LXQt, Xfce, …) systemds `graphical-session.target` nicht
aktivieren.

Entfernen:

```sh
./install.sh --uninstall
```

## Weitere Programme

Welche Programme betroffen sind, steht in `~/.config/dragtab.conf`
(WM_CLASS-Namen, ohne Rücksicht auf Groß- und Kleinschreibung):

```sh
DRAGTAB_CLASSES="thunderbird firefox"
```

Danach `systemctl --user restart dragtab`. Den WM_CLASS-Namen eines Fensters
zeigt `xprop WM_CLASS` nach einem Klick ins Fenster.

## Fehlersuche

```sh
systemctl --user status dragtab
dragtab -v thunderbird     # im Vordergrund, mit Protokoll
```

## Grenzen

- Die Reihenfolge folgt der Stapelreihenfolge der Fenster. Die stimmt meist,
  aber nicht immer mit der Reihenfolge der letzten Benutzung überein, die der
  Fenstermanager verwendet.
- Minimierte Fenster werden übersprungen.

## Lizenz

GPL-3.0-or-later, siehe [LICENSE](LICENSE).
