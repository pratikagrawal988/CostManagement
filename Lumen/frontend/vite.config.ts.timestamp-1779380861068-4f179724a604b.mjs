import "node:module";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import.meta.url;
var vite_config_default = defineConfig({
	plugins: [react()],
	server: {
		host: "0.0.0.0",
		port: 5175,
		proxy: { "/api": {
			target: "http://127.0.0.1:8088",
			changeOrigin: true
		} }
	},
	build: {
		outDir: "dist",
		sourcemap: false
	}
});
//#endregion
export { vite_config_default as default };

//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoidml0ZS5jb25maWcuanMiLCJuYW1lcyI6W10sInNvdXJjZXMiOlsiL3Nlc3Npb25zL2JvbGQtZmVydmVudC1nYWxpbGVvL21udC9GaW5PcHMvUmVjb21tZW5kYXRpb24tZW5naW5lL2Zyb250ZW5kL3ZpdGUuY29uZmlnLnRzIl0sInNvdXJjZXNDb250ZW50IjpbImltcG9ydCB7IGRlZmluZUNvbmZpZyB9IGZyb20gJ3ZpdGUnO1xuaW1wb3J0IHJlYWN0IGZyb20gJ0B2aXRlanMvcGx1Z2luLXJlYWN0JztcblxuZXhwb3J0IGRlZmF1bHQgZGVmaW5lQ29uZmlnKHtcbiAgcGx1Z2luczogW3JlYWN0KCldLFxuICBzZXJ2ZXI6IHtcbiAgICBob3N0OiAnMC4wLjAuMCcsXG4gICAgcG9ydDogNTE3NSxcbiAgICBwcm94eToge1xuICAgICAgJy9hcGknOiB7XG4gICAgICAgIHRhcmdldDogJ2h0dHA6Ly8xMjcuMC4wLjE6ODA4OCcsXG4gICAgICAgIGNoYW5nZU9yaWdpbjogdHJ1ZSxcbiAgICAgIH0sXG4gICAgfSxcbiAgfSxcbiAgYnVpbGQ6IHtcbiAgICBvdXREaXI6ICdkaXN0JyxcbiAgICBzb3VyY2VtYXA6IGZhbHNlLFxuICB9LFxufSk7XG4iXSwibWFwcGluZ3MiOiI7Ozs7QUFHQSxJQUFBLHNCQUFlLGFBQWE7Q0FDMUIsU0FBUyxDQUFDLE1BQU0sQ0FBQztDQUNqQixRQUFRO0VBQ04sTUFBTTtFQUNOLE1BQU07RUFDTixPQUFPLEVBQ0wsUUFBUTtHQUNOLFFBQVE7R0FDUixjQUFjO0VBQ2hCLEVBQ0Y7Q0FDRjtDQUNBLE9BQU87RUFDTCxRQUFRO0VBQ1IsV0FBVztDQUNiO0FBQ0YsQ0FBQyJ9