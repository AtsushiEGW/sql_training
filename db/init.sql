
begin;

drop table if exists products;

create table products (
  product_id serial primary key,
  product_name text not null,
  price numeric(10,2) not null,
  created_at timestamp default now()
);

insert into products (product_name, price) values
('Widget A', 1200.00),
('Widget B', 980.00),
('Widget C', 1500.00);
commit;