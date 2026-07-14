from notifier import load_config, validate_config, monitor_loop


def main():
    cfg = load_config()
    token, chat_id = validate_config(cfg)
    monitor_loop(cfg, token, chat_id)


if __name__ == "__main__":
    main()
