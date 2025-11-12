import network
import time
import sys

TARGET_SSID = "Andrés"
CSV_FILE = "rssi_data.csv"
NUM_MEDIDAS = 10
SLEEP_BETWEEN_SCANS = 0.5
DISTANCIAS = None  # O por ejemplo: [1, 2, 3, 4, 5]

def safe_decode(b):
    if not b:
        return "<ssid_vacio>"
    try:
        return b.decode('utf-8', 'ignore')
    except:
        return str(b)

def scan_for_ssid(wlan, target_ssid):
    try:
        redes = wlan.scan()
    except Exception as e:
        print("Error en wlan.scan():", e)
        return []
    resultados = []
    for r in redes:
        try:
            ssid_bytes = r[0]
            rssi = r[3]
        except Exception:
            continue
        ssid = safe_decode(ssid_bytes)
        resultados.append((ssid, rssi))
    return resultados

def medir_en_distancia(wlan, target_ssid, num_medidas):
    total = 0
    cont = 0
    for i in range(num_medidas):
        redes = scan_for_ssid(wlan, target_ssid)
        found = False
        for ssid, rssi in redes:
            if ssid == target_ssid:
                total += rssi
                cont += 1
                found = True
                break
        if not found:
            print(f"  medida {i+1}: SSID no encontrado")
        else:
            print(f"  medida {i+1}: {rssi} dBm")
        time.sleep(SLEEP_BETWEEN_SCANS)
    if cont == 0:
        return None
    return total / cont

def guardar_csv(filename, datos):
    try:
        with open(filename, "w") as f:
            f.write("Distancia(m),RSSI(dBm)\n")
            for d, r in datos:
                f.write("{},{}\n".format(d, r))
        return True
    except Exception as e:
        print("Error guardando CSV:", e)
        return False

def main():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    time.sleep(0.5)
    print("WLAN activa:", wlan.active())

    resultados = []

    if DISTANCIAS is not None:
        modo_auto = True
        lista_distancias = DISTANCIAS
        print("Modo automático. Distancias:", lista_distancias)
    else:
        modo_auto = False
        lista_distancias = []

    try:
        if modo_auto:
            for distancia in lista_distancias:
                print(f"\n==> Midiendo en {distancia} m ...")
                rssi_prom = medir_en_distancia(wlan, TARGET_SSID, NUM_MEDIDAS)
                if rssi_prom is None:
                    print("  ⚠️ AP no encontrado en este punto (salteando).")
                    resultados.append((distancia, "NaN"))
                else:
                    print(f"  RSSI promedio: {rssi_prom:.2f} dBm")
                    resultados.append((distancia, round(rssi_prom, 2)))
        else:
            distancia = 1
            while True:
                try:
                    input(f"\nColócate a {distancia} m y presiona Enter para medir (Ctrl+C para salir)...")
                except KeyboardInterrupt:
                    print("\nInterrupción por teclado. Saliendo.")
                    break
                except Exception as e:
                    print("Advertencia: input() falló:", e)
                    print("Define DISTANCIAS = [1,2,3,...] para modo automático.")
                    break

                print("  Realizando mediciones...")
                rssi_prom = medir_en_distancia(wlan, TARGET_SSID, NUM_MEDIDAS)
                if rssi_prom is None:
                    print("  ⚠️ No se encontró el AP en ninguna medición.")
                    cont = input("¿Continuar con otra distancia? (s/n): ").strip().lower()
                    if cont != 's':
                        break
                    distancia += 1
                    continue

                resultados.append((distancia, round(rssi_prom, 2)))
                print(f"Distancia: {distancia} m | RSSI promedio: {rssi_prom:.2f} dBm")
                cont = input("¿Continuar con otra distancia? (s/n): ").strip().lower()
                if cont != 's':
                    break
                distancia += 1

    except Exception as e:
        print("Error inesperado en mediciones:", e)

    if resultados:
        ok = guardar_csv(CSV_FILE, resultados)
        if ok:
            print(f"\n✅ Datos guardados en {CSV_FILE}")
            for d, r in resultados:
                print(f"  {d} m -> {r}")
        else:
            print("No se pudo guardar el archivo CSV.")
    else:
        print("No hay resultados para guardar.")

if __name__ == "__main__":
    main()
