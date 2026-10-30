/* Kleiner SDL2-Test fuer Sailfish OS: Braucht der Wayland-Hintergrund von
 * SDL2 ein EGL-Fenster (libhybris/Mali) oder funktioniert der shm-Pfad?
 * Aufruf: sdltest plain   -> ohne SDL_WINDOW_OPENGL
 *         sdltest gl      -> mit SDL_WINDOW_OPENGL (Vergleich)         */
#include <SDL2/SDL.h>

int main(int argc, char **argv)
{
    Uint32 flags = SDL_WINDOW_ALLOW_HIGHDPI;
    const char *mode = "plain";

    if (argc > 1 && argv[1][0] == 'g') {
        flags |= SDL_WINDOW_OPENGL;
        mode = "gl";
    }

    SDL_Log("SDL-Videotreiber: %s", SDL_GetVideoDriver(0));
    SDL_Window *w = SDL_CreateWindow("PseudoPet SDL-Test", 0, 0, 360, 640, flags);
    if (!w) {
        SDL_Log("CreateWindow FEHLER: %s", SDL_GetError());
        return 2;
    }
    SDL_Log("Fenster OK (%s)", mode);

    SDL_Surface *s = SDL_GetWindowSurface(w);
    if (!s) {
        SDL_Log("GetWindowSurface FEHLER: %s", SDL_GetError());
    } else {
        SDL_FillRect(s, NULL, SDL_MapRGB(s->format, 30, 90, 30));
        SDL_UpdateWindowSurface(w);
        SDL_Log("Surface-Fuellung gepusht: %dx%d", s->w, s->h);
    }
    SDL_Delay(4000);
    SDL_DestroyWindow(w);
    SDL_Log("Test durchgelaufen");
    return 0;
}
