# DragTab

**Alt+Tab while dragging – even out of Thunderbird and other GTK applications.**

[Deutsche Fassung](README.de.md)

On X11, try dragging an email out of Thunderbird and pressing Alt+Tab to reach
the target window: nothing happens. Doing the same with a file from the file
manager works fine.

The reason: GTK grabs the keyboard while a drag is in progress, so the window
manager (Openbox, Xfwm, …) never sees Alt+Tab. DragTab listens to the raw
XInput2 events the X server delivers anyway, detects Alt+Tab while the left
mouse button is held and raises the next window. Just drop the email there.

- The window switches **immediately** when you press Tab, not only when you
  release Alt.
- Press Tab again to go further, Shift+Alt+Tab to go back.
- Without a drag nothing changes – Alt+Tab is still handled by your window
  manager.
- DragTab only acts for the applications you tell it about (default:
  Thunderbird), so it does not switch twice in applications where Alt+Tab
  already works.

## Requirements

- an X11 session (on Wayland the compositor handles dragging itself)
- an EWMH-compliant window manager (Openbox, Xfwm, Marco, KWin, …)
- Python 3, `xdotool`, `xprop` and libXi

On Debian/Ubuntu:

```sh
sudo apt install python3 xdotool x11-utils libxi6
```

Tested on Ubuntu 22.04 with LXQt and Openbox.

## Installation

```sh
git clone https://github.com/Codatus/dragtab.git
cd dragtab
./install.sh
```

The script installs for the current user:

| File | Purpose |
|---|---|
| `~/.local/bin/dragtab` | the program |
| `~/.config/systemd/user/dragtab.service` | systemd user service, restarts after crashes |
| `~/.config/autostart/dragtab-start.desktop` | starts the service at login |

The autostart entry is needed because many lightweight desktops (LXQt, Xfce, …)
never activate systemd's `graphical-session.target`.

To remove it:

```sh
./install.sh --uninstall
```

## More applications

The applications DragTab handles are listed in `~/.config/dragtab.conf`
(WM_CLASS names, case-insensitive):

```sh
DRAGTAB_CLASSES="thunderbird firefox"
```

Then run `systemctl --user restart dragtab`. To find a window's WM_CLASS, run
`xprop WM_CLASS` and click into the window.

## Troubleshooting

```sh
systemctl --user status dragtab
dragtab -v thunderbird     # in the foreground, with log output
```

## Limitations

- Windows are cycled in stacking order. That usually, but not always, matches
  the most-recently-used order your window manager uses.
- Minimised windows are skipped.

## License

GPL-3.0-or-later, see [LICENSE](LICENSE).
