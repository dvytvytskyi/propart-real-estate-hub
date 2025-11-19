#!/bin/bash

# Швидка перевірка логів коментарів

echo "🔍 Перевірка останніх логів коментарів..."
echo ""

sudo journalctl -u propart -n 200 --no-pager | grep -E "(comment|note|deal|HubSpot|ERROR|❌|✅|⚠️|📝|🔗)" | tail -30

echo ""
echo "💡 Для детальнішої перевірки виконайте:"
echo "   sudo journalctl -u propart -f | grep -i 'comment\|note\|deal'"

