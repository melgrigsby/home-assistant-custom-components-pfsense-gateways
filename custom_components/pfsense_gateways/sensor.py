
<?php
/*
 * pfSense Gateway Status JSON
 * Based on the original script by Alexander Morris.
 *
 * Updated to:
 * - Support multiple gateways on the same interface
 * - Use unique gateway names as JSON keys
 * - Preserve optional interface traffic rates
 * - Avoid undefined query parameter warnings
 */

##|+PRIV
##|*IDENT=page-status-gateways-json
##|*NAME=Status: Gateways json
##|*DESCR=Allow access to gateway status data via JSON.
##|*MATCH=status_gateways_json.php*
##|-PRIV

// CHANGE THIS to your own secret key.
$secret_key = 'CHANGE_ME';

if (!hash_equals($secret_key, (string) ($_GET['key'] ?? ''))) {
    http_response_code(403);
    exit('invalidRequest');
}

require_once('interfaces.inc');

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

$include_rates = (($_GET['rates'] ?? '0') === '1');

$a_gateways = return_gateways_array();
$gateways_status = return_gateways_status(true);

$pfgateways = array();

function get_interface_rates($iface)
{
    $realif = get_real_interface($iface);

    if (empty($realif)) {
        return null;
    }

    $before = pfSense_get_interface_stats($realif);

    $start = microtime(true);
    usleep(100000);

    $after = pfSense_get_interface_stats($realif);
    $elapsed = microtime(true) - $start;

    if ($elapsed <= 0 ||
        !isset($before['inbytes'], $before['outbytes'],
               $after['inbytes'], $after['outbytes'])) {
        return null;
    }

    return array(
        'inKbps' => abs($after['inbytes'] - $before['inbytes'])
                    * 8 / $elapsed / 1000,
        'outKbps' => abs($after['outbytes'] - $before['outbytes'])
                     * 8 / $elapsed / 1000
    );
}

// Preserve the original optional LAN traffic entry.
if ($include_rates) {
    $lan_rates = get_interface_rates('lan');

    if ($lan_rates !== null) {
        $pfgateways['lan'] = array_merge(
            array('interface' => get_real_interface('lan')),
            $lan_rates
        );
    }
}

// Process each gateway individually.
foreach ($gateways_status as $a_gateway) {

    $gwname = $a_gateway['name'] ?? null;

    if (empty($gwname) || !isset($a_gateways[$gwname])) {
        continue;
    }

    $gateway = $a_gateways[$gwname];

    $iface = $gateway['friendlyiface'] ?? '';
    $realif = $gateway['interface'] ?? '';

    $status = $a_gateway['status'] ?? 'unknown';

    if ($status === 'none') {
        $status = 'okay';
    }

    // Use the gateway NAME as the unique JSON key.
    $pfgateways[$gwname] = array(
        'interface'     => $realif,
        'friendlyiface' => $iface,
        'name'          => $gwname,
        'status'        => $status,
        'monitorip'     => $a_gateway['monitorip'] ?? '',
        'sourceip'      => $a_gateway['srcip'] ?? '',
        'gatewayip'     => $gateway['gateway'] ?? '',
        'delay'         => $a_gateway['delay'] ?? '',
        'loss'          => $a_gateway['loss'] ?? ''
    );

    if ($include_rates && !empty($iface)) {
        $rates = get_interface_rates($iface);

        if ($rates !== null) {
            $pfgateways[$gwname] = array_merge(
                $pfgateways[$gwname],
                $rates
            );
        }
    }
}

echo json_encode(
    $pfgateways,
    JSON_PRETTY_PRINT | JSON_INVALID_UTF8_SUBSTITUTE
);
?>
