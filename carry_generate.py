from BrentKung import BrentKung

if __name__ == '__main__':
    brent_kung = BrentKung()
    # fanout = brent_kung.compute_fanout()
    # brent_kung.build_jsim()
    # brent_kung.get_carries(24, 15, subtract=True)
    brent_kung.get_carries(0x55555555, 0x55555555, subtract=False)