from daqhats import hat_list, HatIDs, mcc128

def main():
    # Liste des cartes HAT détectées
    hats = hat_list(filter_by_id=HatIDs.ANY)
    if len(hats) == 0:
        print("No HATs found.")
        return

    # Affiche les cartes détectées
    for hat in hats:
        print(f"Found {hat.product_name} at address {hat.address}")

    # Sélectionne la première carte MCC 128 détectée
    for hat in hats:
        if hat.id == HatIDs.MCC_128:
            address = hat.address
            board = mcc128(address)
            try:
                print(f"Selected MCC 128 at address {address}")
                # Lecture d'un canal pour vérifier la communication
                value = board.a_in_read(0)
                print(f"Channel 0 value: {value}")
            except Exception as e:
                print(f"Error accessing board at address {address}: {e}")

if __name__ == "__main__":
    main()
    
