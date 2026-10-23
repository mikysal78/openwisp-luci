// Crea sul router una sessione LuCI per l'utente USER, con gli stessi
// permessi che rpcd gli darebbe al login con la password (sezione login di
// /etc/config/rpcd e ACL di /usr/share/rpcd/acl.d), e stampa l'ID.
// openwisp-luci la esegue via SSH con: ucode -e '<questo file>'
// dopo aver sostituito __USER__ con il nome utente in JSON.
import { glob, readfile, open } from "fs";
import { cursor } from "uci";
import { connect } from "ubus";

let user = __USER__;
let login = null;
cursor().foreach("rpcd", "login", (s) => {
	if (s.username == user)
		login = s;
});
if (!login) {
	warn("utente rpcd non trovato\n");
	exit(2);
}

function allowed(perm, group) {
	let patterns = login[perm];
	if (type(patterns) == "string")
		patterns = [ patterns ];
	for (let p in patterns ?? [])
		if (wildcard(group, p))
			return true;
	return false;
}

let bus = connect();
let timeout = +(cursor().get("luci", "sauth", "sessiontime") ?? 3600);
let sid = bus.call("session", "create", { timeout })?.ubus_rpc_session;
if (!sid) {
	warn("sessione non creata\n");
	exit(3);
}

function grant(scope, objects) {
	if (length(objects))
		bus.call("session", "grant", { ubus_rpc_session: sid, scope, objects });
}

// come rpc_login_setup_acls() di rpcd
for (let path in glob("/usr/share/rpcd/acl.d/*.json")) {
	let acl = json(readfile(path) ?? "{}");
	for (let group, spec in acl) {
		for (let perm in [ "read", "write" ]) {
			if (type(spec?.[perm]) != "object" || !allowed(perm, group))
				continue;
			grant("access-group", [ [ group, perm ] ]);
			for (let scope, items in spec[perm]) {
				let objects = [];
				if (type(items) == "array")
					for (let name in items)
						push(objects, [ name, perm ]);
				else if (type(items) == "object")
					for (let name, funcs in items)
						for (let f in (type(funcs) == "array" ? funcs : []))
							push(objects, [ name, f ]);
				grant(scope, objects);
			}
		}
	}
}

let rnd = open("/dev/urandom");
let token = join("", map(split(rnd.read(16), ""), (c) => sprintf("%02x", ord(c))));
rnd.close();
bus.call("session", "set", { ubus_rpc_session: sid, values: { username: user, token } });
print(sid, "\n");
