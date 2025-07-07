module.exports = {
  apps: [{
    name: "ai-trader-bot",
    script: "main.py",
    interpreter: "./.venv/bin/python",
    watch: true,
    ignore_watch: [".venv", ".git", "logs"],
    max_restarts: 10,
    restart_delay: 5000
  }]
};
