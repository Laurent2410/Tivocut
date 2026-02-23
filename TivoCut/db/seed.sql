INSERT OR IGNORE INTO materials(name) VALUES ('PVC'),('ALU'),('HPL');
INSERT OR IGNORE INTO cores(name) VALUES ('XPS33');

INSERT OR IGNORE INTO panel_formats(width_mm,height_mm,label) VALUES
(900,1050,'900x1050'),
(900,2100,'900x2100'),
(1150,3000,'1150x3000'),
(1500,3000,'1500x3000');

INSERT OR IGNORE INTO finishes(name,multiplier,surcharge) VALUES
('UNICOLORE',1.0,0.0),
('BICOLORE',1.0,0.0);

INSERT OR IGNORE INTO suppliers(name) VALUES ('FOURNISSEUR_A');