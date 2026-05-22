%define debug_package %{nil}

%global appname pyrolist
%global appver  VERSION_PLACEHOLDER

Name:           %{appname}
Version:        %{appver}
Release:        1%{?dist}
Summary:        Cliente de escritorio para YouTube Music
License:        GPL-3.0-or-later
URL:            https://github.com/Eirom16/%{appname}
Source0:        %{appname}-%{appver}.tar.gz

BuildArch:      x86_64
BuildRequires:  python3-devel >= 3.12
BuildRequires:  python3-pip
Requires:       python3 >= 3.12
Requires:       vlc
Requires:       vlc-libs
Requires:       python3-dbus
Requires:       dbus-libs
Requires:       qt6-qtbase
AutoReqProv:    no

%description
Pyrolist es un cliente moderno de YouTube Music para escritorio Linux
con soporte de letras sincronizadas, ecualizador paramétrico de 10 bandas,
Discord Rich Presence, scrobbling a Last.fm e integración MPRIS2.

%prep
%autosetup -n %{appname}-%{appver}

%build
# No compilation required for pure Python

%install
# Instalar dependencias Python directamente en buildroot
pip3 install --isolated --break-system-packages --root="%{buildroot}" --prefix=/usr \
    ytmusicapi yt-dlp syncedlyrics qasync qt-material \
    "sqlalchemy[asyncio]" aiosqlite pydantic httpx \
    loguru pystray pillow pylast pypresence python-vlc

# Código fuente
install -dm755 %{buildroot}/usr/lib/%{appname}
cp -r src/%{appname} %{buildroot}/usr/lib/%{appname}/app
cp -r assets         %{buildroot}/usr/lib/%{appname}/assets

# Lanzador
install -Dm755 /dev/stdin %{buildroot}/usr/bin/%{appname} << 'LAUNCHER'
#!/bin/bash
export PYROLIST_ASSETS="/usr/lib/pyrolist/assets"
exec python3 /usr/lib/pyrolist/app/main.py "$@"
LAUNCHER

# Integración escritorio
install -Dm644 packaging/pyrolist.desktop \
    %{buildroot}/usr/share/applications/%{appname}.desktop
install -Dm644 assets/icon.png \
    %{buildroot}/usr/share/pixmaps/%{appname}.png
install -Dm644 assets/icon.png \
    %{buildroot}/usr/share/icons/hicolor/256x256/apps/%{appname}.png

%post
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database /usr/share/applications || true
fi
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -f /usr/share/icons/hicolor || true
fi

%postun
if [ "$1" -eq 0 ]; then
    rm -rf /usr/lib/%{appname} || true
fi

%files
%license LICENSE
%doc README.md
/usr/bin/%{appname}
/usr/lib/%{appname}/
/usr/share/applications/%{appname}.desktop
/usr/share/pixmaps/%{appname}.png
/usr/share/icons/hicolor/256x256/apps/%{appname}.png

%changelog
* VERSION_DATE Eirom16 <eirom16@users.noreply.github.com> - VERSION_PLACEHOLDER-1
- Release automatizado desde GitHub Actions
