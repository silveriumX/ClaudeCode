<?xml version="1.0" encoding="UTF-8"?>
<map version="1.0.0">
  <node TEXT="Финансовая система" ID="root" POSITION="right">
    <node TEXT="1. Маркетплейсы" ID="block1" POSITION="right">
      <node TEXT="WB" ID="wb">
        <node TEXT="DBZ" ID="wb_dbz"/>
        <node TEXT="MN" ID="wb_mn"/>
        <node TEXT="VAS" ID="wb_vas"/>
        <node TEXT="LYA" ID="wb_lya"/>
        <node TEXT="MAKS" ID="wb_maks"/>
        <node TEXT="LIFE" ID="wb_life"/>
        <node TEXT="HUB" ID="wb_hub"/>
        <node TEXT="ALEX" ID="wb_alex"/>
      </node>
      <node TEXT="Озон" ID="ozon">
        <node TEXT="VAS" ID="ozon_vas"/>
        <node TEXT="LYA" ID="ozon_lya"/>
        <node TEXT="LIFE" ID="ozon_life"/>
        <node TEXT="HUB" ID="ozon_hub"/>
        <node TEXT="ALEX" ID="ozon_alex"/>
      </node>
    </node>
    <node TEXT="2. Юрлица" ID="block2" POSITION="right">
      <node TEXT="DBZ" ID="dbz"/>
      <node TEXT="MN" ID="mn"/>
      <node TEXT="VAS" ID="vas"/>
      <node TEXT="LYA" ID="lya"/>
      <node TEXT="MAKS" ID="maks"/>
      <node TEXT="LIFE" ID="life"/>
      <node TEXT="ALEX" ID="alex"/>
      <node TEXT="HUB" ID="hub"/>
    </node>
    <node TEXT="3. Бизнес-банк" ID="block3" POSITION="right">
      <node TEXT="Расчётные счета (1:1 с юрлицами)" ID="banks">
        <node TEXT="Р/с DBZ" ID="bank_dbz"/>
        <node TEXT="Р/с MN" ID="bank_mn"/>
        <node TEXT="Р/с VAS" ID="bank_vas"/>
        <node TEXT="Р/с LYA" ID="bank_lya"/>
        <node TEXT="Р/с MAKS" ID="bank_maks"/>
        <node TEXT="Р/с LIFE" ID="bank_life"/>
        <node TEXT="Р/с ALEX" ID="bank_alex"/>
        <node TEXT="Р/с HUB" ID="bank_hub"/>
      </node>
      <node TEXT="Оплата по безналу" ID="expense_non_cash"/>
      <node TEXT="Налоги" ID="expense_taxes"/>
    </node>
    <node TEXT="4. Личные карты" ID="block4" POSITION="right">
      <node TEXT="Личные карты физлица (у каждого юрлица свои)" ID="cards"/>
      <node TEXT="Маркет-карта (СБП на карту)" ID="market_card"/>
    </node>
    <node TEXT="5. Варианты с карт" ID="block5" POSITION="right">
      <node TEXT="Наличные (снятие по юрлицам)" ID="cash"/>
      <node TEXT="Сейф на складе (наличные → через трейдера → USDT)" ID="safe_warehouse"/>
      <node TEXT="P2P Обмен (карта → USDT; Bybit через P2P переводы)" ID="p2p_exchange"/>
      <node TEXT="Оплата сервисов" ID="service_payments"/>
      <node TEXT="Зарплата ИП" ID="ip_salary"/>
    </node>
    <node TEXT="6. USDT-кошельки" ID="block6" POSITION="right">
      <node TEXT="USDT Зарплаты (холодный)" ID="usdt1"/>
      <node TEXT="RUB/BYN Зарплаты (холодный)" ID="usdt2"/>
      <node TEXT="Разные выплаты (холодный)" ID="usdt3"/>
      <node TEXT="Аргентина (холодный)" ID="usdt4"/>
      <node TEXT="Китай/Карго (холодный)" ID="usdt5"/>
      <node TEXT="Холодный транзит (Bybit → Карго/HTX)" ID="cold_wallet"/>
      <node TEXT="Кошелёк Карго" ID="cargo_wallet"/>
    </node>
    <node TEXT="7. Сервисы" ID="block7" POSITION="right">
      <node TEXT="P2P Платформы (BitPapa; пополнение с холодного USDT)" ID="p2p_platforms"/>
      <node TEXT="Bybit (пополнение через P2P переводы; пока DBZ)" ID="bybit"/>
      <node TEXT="HTX (юани Alipay, Китай)" ID="htx"/>
    </node>
    <node TEXT="8. Получатели" ID="block8" POSITION="right">
      <node TEXT="Сотрудники (оплаты с P2P)" ID="employees"/>
      <node TEXT="Поставщики (Китай, Карго)" ID="suppliers"/>
      <node TEXT="Прочие (дизайнеры, курьеры, сервисы)" ID="others"/>
    </node>
  </node>
</map>
